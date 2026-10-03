"""Add Phase 2 identity, membership, and owner-coverage foundations."""

# DDL contains intentionally literal SQL function bodies and catalog checks.
# ruff: noqa: E501

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019_phase2_bootstrap_membership"
down_revision: str | None = "0018_current_pointer_same_parent_integrity"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


PHASE2_TABLES = (
    "project_memberships",
    "project_role_assignments",
    "project_membership_events",
    "project_role_events",
    "actor_subject_bindings",
    "actor_subject_binding_events",
    "bootstrap_records",
    "actor_enrollment_challenges",
)


def _install_functions() -> None:
    op.execute(
        """
        CREATE FUNCTION rb_phase2_lock_project(p_project_id uuid) RETURNS void
        LANGUAGE plpgsql AS $$
        BEGIN
            PERFORM pg_advisory_xact_lock(hashtextextended('researchbase-project:' || p_project_id::text, 0));
            PERFORM id FROM projects WHERE id = p_project_id FOR UPDATE;
        END
        $$;

        CREATE FUNCTION rb_phase2_owner_coverage(p_project_id uuid) RETURNS boolean
        LANGUAGE plpgsql STABLE AS $$
        DECLARE
            v_started timestamptz;
            v_coverage tstzmultirange;
        BEGIN
            SELECT min(occurred_at) INTO v_started
              FROM project_membership_events e
              JOIN project_memberships m ON m.id = e.membership_id
             WHERE m.project_id = p_project_id
               AND e.event_kind IN ('FIRST_BOOTSTRAP', 'PROJECT_ENROLLMENT');
            IF v_started IS NULL THEN
                RETURN true;
            END IF;

            SELECT range_agg(tstzrange(owner_start, owner_end, '[)'))
              INTO v_coverage
              FROM (
                    SELECT greatest(v_started, m.started_at, r.effective_from, b.bound_at) AS owner_start,
                           least(r.effective_until, terminal.ended_at, b.revoked_at, a.retired_at) AS owner_end
                      FROM project_role_assignments r
                      JOIN project_memberships m
                        ON m.id = r.membership_id
                       AND m.project_id = r.project_id
                       AND m.actor_id = r.actor_id
                      JOIN actors a ON a.id = r.actor_id
                      JOIN actor_subject_bindings b
                        ON b.actor_id = r.actor_id
                       AND b.status IN ('ACTIVE', 'REVOKED')
                      LEFT JOIN LATERAL (
                          SELECT min(e.occurred_at) AS ended_at
                            FROM project_membership_events e
                           WHERE e.membership_id = m.id
                             AND e.event_kind IN ('SUSPENDED', 'ENDED')
                      ) terminal ON true
                     WHERE r.project_id = p_project_id
                       AND r.role = 'OWNER'
                       AND (r.effective_until IS NULL OR r.effective_until > r.effective_from)
                       AND (terminal.ended_at IS NULL OR terminal.ended_at > m.started_at)
                       AND (b.revoked_at IS NULL OR b.revoked_at > b.bound_at)
                       AND (a.retired_at IS NULL OR a.retired_at > b.bound_at)
                       AND r.effective_from IS NOT NULL
                       AND b.bound_at IS NOT NULL
              ) intervals
             WHERE owner_end IS NULL OR owner_end > owner_start;

            RETURN coalesce(v_coverage @> tstzrange(v_started, NULL, '[)'), false);
        END
        $$;

        CREATE FUNCTION rb_phase2_check_owner_coverage() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            v_project_id uuid;
            v_actor_id uuid;
        BEGIN
            IF TG_TABLE_NAME = 'project_memberships' THEN
                v_project_id := coalesce(NEW.project_id, OLD.project_id);
            ELSIF TG_TABLE_NAME = 'project_role_assignments' THEN
                v_project_id := coalesce(NEW.project_id, OLD.project_id);
            ELSIF TG_TABLE_NAME = 'actor_subject_bindings' THEN
                v_actor_id := coalesce(NEW.actor_id, OLD.actor_id);
            ELSIF TG_TABLE_NAME = 'actors' THEN
                v_actor_id := coalesce(NEW.id, OLD.id);
            ELSE
                v_project_id := NULL;
            END IF;

            IF v_project_id IS NOT NULL AND NOT rb_phase2_owner_coverage(v_project_id) THEN
                RAISE EXCEPTION 'project owner coverage gap' USING ERRCODE = '23514',
                    CONSTRAINT = 'ck_project_owner_coverage';
            END IF;
            IF v_actor_id IS NOT NULL THEN
                FOR v_project_id IN
                    SELECT DISTINCT m.project_id
                      FROM project_memberships m
                     WHERE m.actor_id = v_actor_id
                     ORDER BY m.project_id
                LOOP
                    IF NOT rb_phase2_owner_coverage(v_project_id) THEN
                        RAISE EXCEPTION 'project owner coverage gap' USING ERRCODE = '23514',
                            CONSTRAINT = 'ck_project_owner_coverage';
                    END IF;
                END LOOP;
            END IF;
            RETURN NULL;
        END
        $$;

        CREATE FUNCTION rb_phase2_guard_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Phase 2 history rows are immutable' USING ERRCODE = '23514',
                CONSTRAINT = 'ck_phase2_immutable';
        END
        $$;

        CREATE FUNCTION rb_phase2_lock_deployment() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            PERFORM pg_advisory_xact_lock(hashtextextended('researchbase-deployment:' || NEW.deployment_id, 0));
            RETURN NEW;
        END
        $$;

        CREATE FUNCTION rb_phase2_lock_changed_project() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            v_project_id uuid;
        BEGIN
            IF TG_TABLE_NAME = 'project_memberships' THEN
                v_project_id := coalesce(NEW.project_id, OLD.project_id);
            ELSIF TG_TABLE_NAME = 'project_role_assignments' THEN
                v_project_id := coalesce(NEW.project_id, OLD.project_id);
            ELSIF TG_TABLE_NAME = 'actors' THEN
                FOR v_project_id IN
                    SELECT DISTINCT m.project_id
                      FROM project_memberships m
                     WHERE m.actor_id = coalesce(NEW.id, OLD.id)
                     ORDER BY m.project_id
                LOOP
                    PERFORM rb_phase2_lock_project(v_project_id);
                END LOOP;
            ELSE
                FOR v_project_id IN
                    SELECT DISTINCT m.project_id
                      FROM project_memberships m
                     WHERE m.actor_id = coalesce(NEW.actor_id, OLD.actor_id)
                     ORDER BY m.project_id
                LOOP
                    PERFORM rb_phase2_lock_project(v_project_id);
                END LOOP;
            END IF;
            IF v_project_id IS NOT NULL THEN
                PERFORM rb_phase2_lock_project(v_project_id);
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END
        $$;

        CREATE FUNCTION rb_phase2_guard_membership_update() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.id IS DISTINCT FROM OLD.id OR NEW.project_id IS DISTINCT FROM OLD.project_id OR
               NEW.actor_id IS DISTINCT FROM OLD.actor_id OR NEW.started_at IS DISTINCT FROM OLD.started_at OR
               NEW.created_by IS DISTINCT FROM OLD.created_by OR NEW.created_at IS DISTINCT FROM OLD.created_at OR
               (OLD.status <> 'ACTIVE') OR NEW.status NOT IN ('SUSPENDED', 'ENDED') OR
               NEW.row_version <> OLD.row_version + 1 OR
               (NEW.status = 'ENDED' AND (NEW.ended_at IS NULL OR NEW.ended_at < OLD.started_at)) OR
               (NEW.status = 'SUSPENDED' AND NEW.ended_at IS NOT NULL) THEN
                RAISE EXCEPTION 'membership update is not a terminal transition'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_project_membership_transition';
            END IF;
            RETURN NEW;
        END
        $$;

        CREATE FUNCTION rb_phase2_guard_role_update() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.id IS DISTINCT FROM OLD.id OR NEW.membership_id IS DISTINCT FROM OLD.membership_id OR
               NEW.project_id IS DISTINCT FROM OLD.project_id OR NEW.actor_id IS DISTINCT FROM OLD.actor_id OR
               NEW.role IS DISTINCT FROM OLD.role OR NEW.effective_from IS DISTINCT FROM OLD.effective_from OR
               NEW.assigned_by IS DISTINCT FROM OLD.assigned_by OR NEW.created_at IS DISTINCT FROM OLD.created_at OR
               OLD.effective_until IS NOT NULL OR NEW.effective_until IS NULL OR
               NEW.effective_until <= OLD.effective_from OR NEW.row_version <> OLD.row_version + 1 THEN
                RAISE EXCEPTION 'role assignment update may only close an open interval'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_project_role_assignment_transition';
            END IF;
            RETURN NEW;
        END
        $$;

        CREATE FUNCTION rb_phase2_guard_binding_update() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.id IS DISTINCT FROM OLD.id OR NEW.actor_id IS DISTINCT FROM OLD.actor_id OR
               NEW.deployment_id IS DISTINCT FROM OLD.deployment_id OR NEW.subject_kind IS DISTINCT FROM OLD.subject_kind OR
               NEW.subject_value IS DISTINCT FROM OLD.subject_value OR NEW.bound_at IS DISTINCT FROM OLD.bound_at OR
               NEW.operator_credential_id IS DISTINCT FROM OLD.operator_credential_id OR
               NEW.subject_credential_id IS DISTINCT FROM OLD.subject_credential_id OR
               NEW.proof_sha256 IS DISTINCT FROM OLD.proof_sha256 OR NEW.proof_record_ref IS DISTINCT FROM OLD.proof_record_ref OR
               NEW.proof_kind IS DISTINCT FROM OLD.proof_kind OR
               NEW.enrollment_challenge_id IS DISTINCT FROM OLD.enrollment_challenge_id OR
               OLD.status <> 'ACTIVE' OR NEW.status <> 'REVOKED' OR NEW.revoked_at IS NULL OR
               NEW.revoked_at <= OLD.bound_at OR NEW.row_version <> OLD.row_version + 1 THEN
                RAISE EXCEPTION 'binding update may only revoke an active subject'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_actor_subject_binding_transition';
            END IF;
            RETURN NEW;
        END
        $$;

        CREATE FUNCTION rb_phase2_guard_challenge_update() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            v_now timestamptz := clock_timestamp();
        BEGIN
            IF NEW.id IS DISTINCT FROM OLD.id OR NEW.deployment_id IS DISTINCT FROM OLD.deployment_id OR
               NEW.actor_id IS DISTINCT FROM OLD.actor_id OR NEW.subject_kind IS DISTINCT FROM OLD.subject_kind OR
               NEW.subject_value IS DISTINCT FROM OLD.subject_value OR
               NEW.subject_credential_id IS DISTINCT FROM OLD.subject_credential_id OR
               NEW.operator_credential_id IS DISTINCT FROM OLD.operator_credential_id OR
               NEW.nonce_digest IS DISTINCT FROM OLD.nonce_digest OR NEW.proof_method IS DISTINCT FROM OLD.proof_method OR
               NEW.issued_at IS DISTINCT FROM OLD.issued_at OR NEW.expires_at IS DISTINCT FROM OLD.expires_at OR
               NEW.request_id IS DISTINCT FROM OLD.request_id OR NEW.row_version <> OLD.row_version + 1 OR
               OLD.status <> 'ISSUED' OR NEW.status NOT IN ('CONSUMED', 'EXPIRED') OR
               (NEW.status = 'CONSUMED' AND (NEW.consumed_at IS NULL OR NEW.result_binding_id IS NULL)) OR
               (NEW.status = 'EXPIRED' AND (NEW.consumed_at IS NOT NULL OR NEW.result_binding_id IS NOT NULL)) OR
               (NEW.status = 'CONSUMED' AND NOT (OLD.issued_at <= v_now AND v_now < OLD.expires_at)) OR
               (NEW.status = 'EXPIRED' AND v_now < OLD.expires_at) THEN
                RAISE EXCEPTION 'challenge update is not a monotonic terminal transition'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_actor_enrollment_challenge_transition';
            END IF;
            RETURN NEW;
        END
        $$;

        CREATE FUNCTION rb_phase2_guard_human_actor() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM actors WHERE id = NEW.actor_id AND actor_type = 'HUMAN') THEN
                RAISE EXCEPTION 'subject binding requires a HUMAN actor'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_actor_subject_binding_human';
            END IF;
            RETURN NEW;
        END
        $$;

        CREATE FUNCTION rb_phase2_require_role_event() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT' AND NOT EXISTS (
                SELECT 1 FROM project_role_events e
                 WHERE e.role_assignment_id = NEW.id AND e.event_kind = 'ASSIGNED'
            ) THEN
                RAISE EXCEPTION 'role assignment requires an ASSIGNED event'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_project_role_initial_event';
            END IF;
            IF TG_OP = 'UPDATE' AND NOT EXISTS (
                SELECT 1 FROM project_role_events e
                 WHERE e.role_assignment_id = NEW.id AND e.event_kind = 'CLOSED'
                   AND e.occurred_at = NEW.effective_until
            ) THEN
                RAISE EXCEPTION 'closed role assignment requires a CLOSED event'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_project_role_closed_event';
            END IF;
            RETURN NULL;
        END
        $$;

        CREATE FUNCTION rb_phase2_require_membership_event() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT' AND NOT EXISTS (
                SELECT 1 FROM project_membership_events e
                 WHERE e.membership_id = NEW.id AND e.prior_status IS NULL
                   AND e.new_status = 'ACTIVE'
                   AND e.event_kind IN ('FIRST_BOOTSTRAP', 'PROJECT_ENROLLMENT', 'ACTIVATED')
            ) THEN
                RAISE EXCEPTION 'membership requires an initial ACTIVE event'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_membership_initial_event';
            END IF;
            IF TG_OP = 'UPDATE' AND NOT EXISTS (
                SELECT 1 FROM project_membership_events e
                 WHERE e.membership_id = NEW.id AND e.prior_status = 'ACTIVE'
                   AND e.new_status = NEW.status AND e.actor_id = NEW.actor_id
                   AND ((NEW.status = 'SUSPENDED' AND e.event_kind = 'SUSPENDED') OR
                        (NEW.status = 'ENDED' AND e.event_kind = 'ENDED'))
                   AND (NEW.status <> 'ENDED' OR e.occurred_at = NEW.ended_at)
            ) THEN
                RAISE EXCEPTION 'membership transition requires its matching event'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_membership_terminal_event';
            END IF;
            RETURN NULL;
        END
        $$;

        CREATE FUNCTION rb_phase2_validate_membership_event() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            v_status varchar(16);
            v_actor uuid;
        BEGIN
            SELECT status, actor_id INTO v_status, v_actor
              FROM project_memberships WHERE id = NEW.membership_id;
            IF NEW.actor_id IS DISTINCT FROM v_actor OR
               (NEW.prior_status IS NULL AND NOT (
                    NEW.event_kind IN ('FIRST_BOOTSTRAP', 'PROJECT_ENROLLMENT', 'ACTIVATED')
                    AND NEW.new_status = 'ACTIVE'
               )) OR
               (NEW.prior_status IS NULL AND NOT EXISTS (
                    SELECT 1 FROM project_memberships m
                     WHERE m.id = NEW.membership_id AND m.started_at = NEW.occurred_at
               )) OR
               (NEW.event_kind = 'SUSPENDED' AND NEW.new_status <> 'SUSPENDED') OR
               (NEW.event_kind = 'ENDED' AND NEW.new_status <> 'ENDED') OR
               (NEW.event_kind IN ('SUSPENDED', 'ENDED') AND NEW.prior_status <> 'ACTIVE') OR
               (NEW.event_kind IN ('SUSPENDED', 'ENDED') AND NEW.new_status IS DISTINCT FROM v_status) OR
               (NEW.event_kind IN ('FIRST_BOOTSTRAP', 'PROJECT_ENROLLMENT', 'ACTIVATED') AND
                    v_status NOT IN ('ACTIVE', 'SUSPENDED', 'ENDED')) OR
               (NEW.event_kind = 'PROJECT_ENROLLMENT' AND NOT EXISTS (
                    SELECT 1 FROM project_memberships m
                    JOIN projects p ON p.id = m.project_id AND p.created_by = m.actor_id
                    JOIN actor_subject_bindings b ON b.actor_id = m.actor_id AND b.status = 'ACTIVE'
                     WHERE m.id = NEW.membership_id
               )) OR
               (NEW.event_kind = 'FIRST_BOOTSTRAP' AND (
                    (SELECT count(*) FROM actors) <> 1 OR
                    (SELECT count(*) FROM projects) <> 1 OR
                    NOT EXISTS (SELECT 1 FROM actors a WHERE a.id = v_actor AND a.actor_type = 'HUMAN') OR
                    NOT EXISTS (SELECT 1 FROM bootstrap_records br WHERE br.first_membership_id = NEW.membership_id)
               )) THEN
                RAISE EXCEPTION 'invalid membership event transition'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_membership_event_transition';
            END IF;
            RETURN NULL;
        END
        $$;

        CREATE FUNCTION rb_phase2_validate_role_event() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            v_project uuid;
            v_actor uuid;
        BEGIN
            SELECT project_id, actor_id INTO v_project, v_actor
              FROM project_role_assignments WHERE id = NEW.role_assignment_id;
            IF v_project IS NULL OR NEW.actor_id IS DISTINCT FROM v_actor OR
               (NEW.event_kind = 'ASSIGNED' AND NOT EXISTS (
                    SELECT 1 FROM project_role_assignments r
                     WHERE r.id = NEW.role_assignment_id AND r.effective_from = NEW.occurred_at
               )) OR
               (NEW.event_kind = 'CLOSED' AND NOT EXISTS (
                    SELECT 1 FROM project_role_assignments r
                     WHERE r.id = NEW.role_assignment_id AND r.effective_until IS NOT NULL
               )) THEN
                RAISE EXCEPTION 'invalid role event transition'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_project_role_event_transition';
            END IF;
            RETURN NULL;
        END
        $$;

        CREATE FUNCTION rb_phase2_validate_binding_event() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            v_binding actor_subject_bindings%ROWTYPE;
        BEGIN
            SELECT * INTO v_binding FROM actor_subject_bindings WHERE id = NEW.binding_id;
            IF NOT FOUND OR NEW.actor_id IS DISTINCT FROM v_binding.actor_id OR
               NEW.operator_credential_id IS DISTINCT FROM v_binding.operator_credential_id OR
               NEW.subject_credential_id IS DISTINCT FROM v_binding.subject_credential_id OR
               NEW.proof_sha256 IS DISTINCT FROM v_binding.proof_sha256 OR
               NEW.proof_record_ref IS DISTINCT FROM v_binding.proof_record_ref OR
               NEW.proof_kind IS DISTINCT FROM v_binding.proof_kind OR
               (NEW.event_kind = 'BOOTSTRAP_BOUND' AND v_binding.proof_kind <> 'OS_PEER') OR
               (NEW.event_kind = 'LEGACY_BOUND' AND v_binding.proof_kind <> 'LEGACY_ATTESTATION') OR
               (NEW.event_kind = 'PROVISIONED' AND v_binding.proof_kind NOT IN ('OS_PEER', 'MTLS_CHALLENGE')) OR
               (NEW.event_kind = 'REVOKED' AND v_binding.status <> 'REVOKED') OR
               (NEW.event_kind <> 'REVOKED' AND v_binding.status <> 'ACTIVE') OR
               (NEW.event_kind = 'REVOKED' AND NEW.occurred_at IS DISTINCT FROM v_binding.revoked_at) OR
               (NEW.event_kind <> 'REVOKED' AND NEW.occurred_at IS DISTINCT FROM v_binding.bound_at) OR
               (NEW.event_kind = 'BOOTSTRAP_BOUND' AND NOT EXISTS (
                    SELECT 1 FROM bootstrap_records br WHERE br.first_binding_id = v_binding.id
               )) THEN
                RAISE EXCEPTION 'binding event does not match binding'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_binding_event_matches_binding';
            END IF;
            RETURN NULL;
        END
        $$;

        CREATE FUNCTION rb_phase2_require_binding_event() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT' AND NOT EXISTS (
                SELECT 1 FROM actor_subject_binding_events e
                 WHERE e.binding_id = NEW.id AND (
                    (NEW.proof_kind = 'LEGACY_ATTESTATION' AND e.event_kind = 'LEGACY_BOUND') OR
                    (NEW.proof_kind = 'OS_PEER' AND e.event_kind IN ('BOOTSTRAP_BOUND', 'PROVISIONED')) OR
                    (NEW.proof_kind = 'MTLS_CHALLENGE' AND e.event_kind = 'PROVISIONED')
                 )
            ) THEN
                RAISE EXCEPTION 'subject binding requires its initial event'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_actor_subject_binding_event_required';
            END IF;
            IF TG_OP = 'UPDATE' AND NOT EXISTS (
                SELECT 1 FROM actor_subject_binding_events e
                 WHERE e.binding_id = NEW.id AND e.event_kind = 'REVOKED'
            ) THEN
                RAISE EXCEPTION 'subject binding revocation requires a REVOKED event'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_actor_subject_binding_event_required';
            END IF;
            RETURN NULL;
        END
        $$;

        CREATE FUNCTION rb_phase2_validate_challenge_binding() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            v_challenge actor_enrollment_challenges%ROWTYPE;
            v_binding actor_subject_bindings%ROWTYPE;
        BEGIN
            IF TG_TABLE_NAME = 'actor_enrollment_challenges' THEN
                SELECT * INTO v_challenge FROM actor_enrollment_challenges WHERE id = NEW.id;
                IF v_challenge.status = 'CONSUMED' THEN
                    SELECT * INTO v_binding FROM actor_subject_bindings WHERE id = v_challenge.result_binding_id;
                ELSE
                    RETURN NULL;
                END IF;
            ELSE
                SELECT * INTO v_binding FROM actor_subject_bindings WHERE id = NEW.id;
                IF v_binding.proof_kind <> 'LEGACY_ATTESTATION' THEN
                    RETURN NULL;
                END IF;
                SELECT * INTO v_challenge FROM actor_enrollment_challenges
                 WHERE id = v_binding.enrollment_challenge_id;
            END IF;
            IF v_challenge.id IS NULL OR v_binding.id IS NULL OR
               v_challenge.status <> 'CONSUMED' OR
               v_challenge.result_binding_id IS DISTINCT FROM v_binding.id OR
               v_binding.enrollment_challenge_id IS DISTINCT FROM v_challenge.id OR
               v_challenge.actor_id IS DISTINCT FROM v_binding.actor_id OR
               v_challenge.deployment_id IS DISTINCT FROM v_binding.deployment_id OR
               v_challenge.subject_kind IS DISTINCT FROM v_binding.subject_kind OR
               v_challenge.subject_value IS DISTINCT FROM v_binding.subject_value OR
               v_challenge.subject_credential_id IS DISTINCT FROM v_binding.subject_credential_id OR
               NOT EXISTS (
                   SELECT 1 FROM actor_subject_binding_events e
                    WHERE e.binding_id = v_binding.id AND e.event_kind = 'LEGACY_BOUND'
               ) THEN
                RAISE EXCEPTION 'challenge and legacy binding are inconsistent'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_challenge_binding_consistency';
            END IF;
            RETURN NULL;
        END
        $$;

        CREATE FUNCTION rb_phase2_validate_bootstrap() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                  FROM actor_subject_bindings b
                  JOIN actors a ON a.id = b.actor_id AND a.actor_type = 'HUMAN'
                  JOIN project_memberships m ON m.id = NEW.first_membership_id
                                             AND m.project_id = NEW.first_project_id
                                             AND m.actor_id = NEW.first_actor_id
                  JOIN project_role_assignments r ON r.id = NEW.first_role_assignment_id
                                                AND r.membership_id = m.id
                                                AND r.project_id = m.project_id
                                                AND r.actor_id = m.actor_id
                                                AND r.role = 'OWNER'
                  JOIN project_membership_events me ON me.membership_id = m.id
                       AND me.event_kind = 'FIRST_BOOTSTRAP'
                  JOIN actor_subject_binding_events be ON be.binding_id = b.id
                       AND be.event_kind = 'BOOTSTRAP_BOUND'
                  WHERE b.id = NEW.first_binding_id AND b.actor_id = NEW.first_actor_id
                    AND b.deployment_id = NEW.deployment_id
            ) THEN
                RAISE EXCEPTION 'bootstrap record does not identify first owner ceremony'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_bootstrap_first_owner';
            END IF;
            RETURN NULL;
        END
        $$;
        """
    )


def upgrade() -> None:
    bind = op.get_bind()
    extension = bind.execute(
        sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'btree_gist'")
    ).scalar_one_or_none()
    if extension is None:
        raise RuntimeError("PR2-00 requires PostgreSQL btree_gist for OWNER exclusion constraints")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    uuid = postgresql.UUID(as_uuid=True)
    timestamp = sa.DateTime(timezone=True)

    op.create_table(
        "project_memberships",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "project_id", uuid, sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "actor_id", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("started_at", timestamp, nullable=False),
        sa.Column("ended_at", timestamp),
        sa.Column(
            "created_by", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("created_at", timestamp, nullable=False),
        sa.Column("row_version", sa.Integer, nullable=False),
        sa.UniqueConstraint(
            "id", "project_id", "actor_id", name="uq_project_memberships_id_project_actor"
        ),
        sa.UniqueConstraint(
            "project_id",
            "actor_id",
            "started_at",
            name="uq_project_memberships_project_actor_started",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'SUSPENDED', 'ENDED')", name="ck_project_memberships_status"
        ),
        sa.CheckConstraint("row_version > 0", name="ck_project_memberships_row_version"),
        sa.CheckConstraint(
            "(status = 'ENDED') = (ended_at IS NOT NULL)",
            name="ck_project_memberships_ended_at_state",
        ),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="ck_project_memberships_ended_after_started",
        ),
    )
    op.create_index(
        "uq_project_memberships_active",
        "project_memberships",
        ["project_id", "actor_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        "ix_project_memberships_actor_status", "project_memberships", ["actor_id", "status"]
    )
    op.create_index(
        "ix_project_memberships_project_status", "project_memberships", ["project_id", "status"]
    )

    op.create_table(
        "project_role_assignments",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("membership_id", uuid, nullable=False),
        sa.Column("project_id", uuid, nullable=False),
        sa.Column("actor_id", uuid, nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("effective_from", timestamp, nullable=False),
        sa.Column("effective_until", timestamp),
        sa.Column(
            "assigned_by", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("created_at", timestamp, nullable=False),
        sa.Column("row_version", sa.Integer, nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="RESTRICT",
            name="fk_project_role_assignments_project",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["actors.id"],
            ondelete="RESTRICT",
            name="fk_project_role_assignments_actor",
        ),
        sa.ForeignKeyConstraint(
            ["membership_id", "project_id", "actor_id"],
            [
                "project_memberships.id",
                "project_memberships.project_id",
                "project_memberships.actor_id",
            ],
            ondelete="RESTRICT",
            name="fk_project_role_assignments_membership_project_actor",
        ),
        sa.UniqueConstraint(
            "id", "project_id", "actor_id", name="uq_project_role_assignments_id_project_actor"
        ),
        sa.CheckConstraint(
            "role IN ('OWNER', 'RESEARCHER', 'REVIEWER', 'APPROVER', 'VIEWER')",
            name="ck_project_role_assignments_role",
        ),
        sa.CheckConstraint("row_version > 0", name="ck_project_role_assignments_row_version"),
        sa.CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="ck_project_role_assignments_effective_interval",
        ),
    )
    op.create_index(
        "uq_project_role_assignments_open",
        "project_role_assignments",
        ["membership_id", "role"],
        unique=True,
        postgresql_where=sa.text("effective_until IS NULL"),
    )
    op.create_index(
        "ix_project_role_assignments_project_role_until",
        "project_role_assignments",
        ["project_id", "role", "effective_until"],
    )
    op.execute(
        "ALTER TABLE project_role_assignments ADD CONSTRAINT ex_project_role_assignments_role_interval EXCLUDE USING gist (membership_id WITH =, role WITH =, tstzrange(effective_from, effective_until, '[)') WITH &&)"
    )

    op.create_table(
        "project_membership_events",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "membership_id",
            uuid,
            sa.ForeignKey("project_memberships.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_kind", sa.String(24), nullable=False),
        sa.Column("prior_status", sa.String(16)),
        sa.Column("new_status", sa.String(16), nullable=False),
        sa.Column(
            "actor_id", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("occurred_at", timestamp, nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("request_id", uuid, nullable=False),
        sa.UniqueConstraint(
            "membership_id", "request_id", name="uq_project_membership_events_membership_request"
        ),
        sa.CheckConstraint(
            "event_kind IN ('FIRST_BOOTSTRAP', 'PROJECT_ENROLLMENT', 'ACTIVATED', 'SUSPENDED', 'ENDED')",
            name="ck_project_membership_events_kind",
        ),
        sa.CheckConstraint(
            "new_status IN ('ACTIVE', 'SUSPENDED', 'ENDED')",
            name="ck_project_membership_events_new_status",
        ),
        sa.CheckConstraint(
            "length(btrim(reason)) > 0", name="ck_project_membership_events_reason_nonblank"
        ),
    )
    op.create_index(
        "ix_project_membership_events_membership_time",
        "project_membership_events",
        ["membership_id", "occurred_at", "id"],
    )

    op.create_table(
        "project_role_events",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "role_assignment_id",
            uuid,
            sa.ForeignKey("project_role_assignments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "actor_id", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("event_kind", sa.String(16), nullable=False),
        sa.Column("occurred_at", timestamp, nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("request_id", uuid, nullable=False),
        sa.UniqueConstraint(
            "role_assignment_id", "request_id", name="uq_project_role_events_assignment_request"
        ),
        sa.CheckConstraint(
            "event_kind IN ('ASSIGNED', 'CLOSED')", name="ck_project_role_events_kind"
        ),
        sa.CheckConstraint(
            "length(btrim(reason)) > 0", name="ck_project_role_events_reason_nonblank"
        ),
    )
    op.create_index(
        "ix_project_role_events_assignment_time",
        "project_role_events",
        ["role_assignment_id", "occurred_at", "id"],
    )

    op.create_table(
        "actor_subject_bindings",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "actor_id", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("deployment_id", sa.Text, nullable=False),
        sa.Column("subject_kind", sa.String(16), nullable=False),
        sa.Column("subject_value", sa.Text, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("bound_at", timestamp, nullable=False),
        sa.Column("revoked_at", timestamp),
        sa.Column("operator_credential_id", sa.Text, nullable=False),
        sa.Column("subject_credential_id", sa.Text, nullable=False),
        sa.Column("proof_sha256", sa.CHAR(64), nullable=False),
        sa.Column("proof_record_ref", sa.Text, nullable=False),
        sa.Column("proof_kind", sa.String(24), nullable=False),
        sa.Column("enrollment_challenge_id", uuid, nullable=True),
        sa.Column("created_at", timestamp, nullable=False),
        sa.Column("row_version", sa.Integer, nullable=False),
        sa.CheckConstraint(
            "subject_kind IN ('OS_UID', 'MTLS_URI')", name="ck_actor_subject_bindings_subject_kind"
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'REVOKED')", name="ck_actor_subject_bindings_status"
        ),
        sa.CheckConstraint(
            "proof_kind IN ('OS_PEER', 'MTLS_CHALLENGE', 'LEGACY_ATTESTATION')",
            name="ck_actor_subject_bindings_proof_kind",
        ),
        sa.CheckConstraint(
            "(proof_kind = 'LEGACY_ATTESTATION') = (enrollment_challenge_id IS NOT NULL)",
            name="ck_actor_subject_bindings_challenge_proof",
        ),
        sa.CheckConstraint("row_version > 0", name="ck_actor_subject_bindings_row_version"),
        sa.CheckConstraint(
            "(status = 'REVOKED') = (revoked_at IS NOT NULL)",
            name="ck_actor_subject_bindings_revoked_at_state",
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at > bound_at",
            name="ck_actor_subject_bindings_revoked_after_bound",
        ),
        sa.CheckConstraint(
            "proof_sha256 ~ '^[0-9a-f]{64}$'", name="ck_actor_subject_bindings_proof_digest"
        ),
        sa.CheckConstraint(
            "length(btrim(deployment_id)) > 0 AND length(btrim(subject_value)) > 0 AND length(btrim(operator_credential_id)) > 0 AND length(btrim(subject_credential_id)) > 0 AND length(btrim(proof_record_ref)) > 0",
            name="ck_actor_subject_bindings_nonblank_text",
        ),
    )
    op.create_index(
        "uq_actor_subject_bindings_active_subject",
        "actor_subject_bindings",
        ["deployment_id", "subject_kind", "subject_value"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        "uq_actor_subject_bindings_actor_subject",
        "actor_subject_bindings",
        ["actor_id", "deployment_id", "subject_kind"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        "ix_actor_subject_bindings_actor_status", "actor_subject_bindings", ["actor_id", "status"]
    )
    op.create_index(
        "ix_actor_subject_bindings_subject",
        "actor_subject_bindings",
        ["deployment_id", "subject_kind", "subject_value"],
    )

    op.create_table(
        "actor_enrollment_challenges",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("deployment_id", sa.Text, nullable=False),
        sa.Column(
            "actor_id", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("subject_kind", sa.String(16), nullable=False),
        sa.Column("subject_value", sa.Text, nullable=False),
        sa.Column("subject_credential_id", sa.Text, nullable=False),
        sa.Column("operator_credential_id", sa.Text, nullable=False),
        sa.Column("nonce_digest", sa.CHAR(64), nullable=False),
        sa.Column("proof_method", sa.String(24), nullable=False),
        sa.Column("issued_at", timestamp, nullable=False),
        sa.Column("expires_at", timestamp, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("consumed_at", timestamp),
        sa.Column("result_binding_id", uuid, nullable=True),
        sa.Column("request_id", uuid, nullable=False),
        sa.Column("row_version", sa.Integer, nullable=False),
        sa.UniqueConstraint(
            "deployment_id", "nonce_digest", name="uq_actor_enrollment_challenges_deployment_nonce"
        ),
        sa.UniqueConstraint(
            "deployment_id", "request_id", name="uq_actor_enrollment_challenges_deployment_request"
        ),
        sa.CheckConstraint(
            "subject_kind IN ('OS_UID', 'MTLS_URI')",
            name="ck_actor_enrollment_challenges_subject_kind",
        ),
        sa.CheckConstraint(
            "status IN ('ISSUED', 'CONSUMED', 'EXPIRED')",
            name="ck_actor_enrollment_challenges_status",
        ),
        sa.CheckConstraint(
            "proof_method IN ('OS_PEER', 'MTLS_CHALLENGE')",
            name="ck_actor_enrollment_challenges_proof_method",
        ),
        sa.CheckConstraint("expires_at > issued_at", name="ck_actor_enrollment_challenges_expiry"),
        sa.CheckConstraint(
            "nonce_digest ~ '^[0-9a-f]{64}$'", name="ck_actor_enrollment_challenges_digest"
        ),
        sa.CheckConstraint(
            "(status = 'CONSUMED') = (consumed_at IS NOT NULL AND result_binding_id IS NOT NULL)",
            name="ck_actor_enrollment_challenges_consumed_result",
        ),
        sa.UniqueConstraint(
            "result_binding_id", name="uq_actor_enrollment_challenges_result_binding"
        ),
        sa.CheckConstraint("row_version > 0", name="ck_actor_enrollment_challenges_row_version"),
        sa.CheckConstraint(
            "length(btrim(deployment_id)) > 0 AND length(btrim(subject_value)) > 0 AND length(btrim(subject_credential_id)) > 0 AND length(btrim(operator_credential_id)) > 0 AND length(btrim(proof_method)) > 0",
            name="ck_actor_enrollment_challenges_nonblank_text",
        ),
    )
    op.create_index(
        "ix_actor_enrollment_challenges_actor_status",
        "actor_enrollment_challenges",
        ["actor_id", "status"],
    )
    op.create_foreign_key(
        "fk_actor_subject_bindings_legacy_challenge",
        "actor_subject_bindings",
        "actor_enrollment_challenges",
        ["enrollment_challenge_id"],
        ["id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_foreign_key(
        "fk_actor_enrollment_challenges_result_binding",
        "actor_enrollment_challenges",
        "actor_subject_bindings",
        ["result_binding_id"],
        ["id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_index(
        "uq_actor_subject_bindings_enrollment_challenge",
        "actor_subject_bindings",
        ["enrollment_challenge_id"],
        unique=True,
        postgresql_where=sa.text("enrollment_challenge_id IS NOT NULL"),
    )

    op.create_table(
        "actor_subject_binding_events",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "binding_id",
            uuid,
            sa.ForeignKey("actor_subject_bindings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "actor_id", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("event_kind", sa.String(24), nullable=False),
        sa.Column("operator_credential_id", sa.Text, nullable=False),
        sa.Column("subject_credential_id", sa.Text, nullable=False),
        sa.Column("proof_sha256", sa.CHAR(64), nullable=False),
        sa.Column("proof_record_ref", sa.Text, nullable=False),
        sa.Column("proof_kind", sa.String(24), nullable=False),
        sa.Column("request_id", uuid, nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("occurred_at", timestamp, nullable=False),
        sa.UniqueConstraint(
            "binding_id", "request_id", name="uq_actor_subject_binding_events_binding_request"
        ),
        sa.CheckConstraint(
            "event_kind IN ('BOOTSTRAP_BOUND', 'LEGACY_BOUND', 'PROVISIONED', 'REVOKED')",
            name="ck_actor_subject_binding_events_kind",
        ),
        sa.CheckConstraint(
            "length(btrim(reason)) > 0", name="ck_actor_subject_binding_events_reason_nonblank"
        ),
        sa.CheckConstraint(
            "proof_kind IN ('OS_PEER', 'MTLS_CHALLENGE', 'LEGACY_ATTESTATION') AND proof_sha256 ~ '^[0-9a-f]{64}$' AND length(btrim(operator_credential_id)) > 0 AND length(btrim(subject_credential_id)) > 0 AND length(btrim(proof_record_ref)) > 0",
            name="ck_actor_subject_binding_events_proof",
        ),
    )
    op.create_index(
        "ix_actor_subject_binding_events_binding_time",
        "actor_subject_binding_events",
        ["binding_id", "occurred_at", "id"],
    )

    op.create_table(
        "bootstrap_records",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("deployment_id", sa.Text, nullable=False, unique=True),
        sa.Column("request_id", uuid, nullable=False, unique=True),
        sa.Column("request_fingerprint", sa.CHAR(64), nullable=False),
        sa.Column("operator_credential_id", sa.Text, nullable=False),
        sa.Column("secret_digest_id", sa.Text, nullable=False),
        sa.Column(
            "first_actor_id", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "first_binding_id",
            uuid,
            sa.ForeignKey("actor_subject_bindings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "first_project_id",
            uuid,
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "first_membership_id",
            uuid,
            sa.ForeignKey("project_memberships.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "first_role_assignment_id",
            uuid,
            sa.ForeignKey("project_role_assignments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("completed_at", timestamp, nullable=False),
        sa.Column("content_hash", sa.CHAR(64), nullable=False),
        sa.Column("hash_scheme", sa.String(32), nullable=False),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$' AND content_hash ~ '^[0-9a-f]{64}$'",
            name="ck_bootstrap_records_hashes",
        ),
        sa.CheckConstraint(
            "hash_scheme = 'sha256-cjson-v1'", name="ck_bootstrap_records_hash_scheme"
        ),
        sa.CheckConstraint(
            "length(btrim(deployment_id)) > 0 AND length(btrim(operator_credential_id)) > 0 AND length(btrim(secret_digest_id)) > 0",
            name="ck_bootstrap_records_nonblank_text",
        ),
    )
    op.create_index(
        "uq_bootstrap_records_singleton", "bootstrap_records", [sa.text("(true)")], unique=True
    )
    op.create_index("ix_bootstrap_records_first_actor", "bootstrap_records", ["first_actor_id"])
    op.create_index("ix_bootstrap_records_first_project", "bootstrap_records", ["first_project_id"])

    _install_functions()

    for table in (
        "project_membership_events",
        "project_role_events",
        "actor_subject_binding_events",
        "bootstrap_records",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION rb_phase2_guard_immutable()"
        )

    op.execute(
        "CREATE CONSTRAINT TRIGGER trg_project_membership_initial_event AFTER INSERT ON project_memberships DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_phase2_require_membership_event()"
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER trg_project_role_initial_event AFTER INSERT OR UPDATE ON project_role_assignments DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_phase2_require_role_event()"
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER trg_project_membership_event_transition AFTER INSERT ON project_membership_events DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_phase2_validate_membership_event()"
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER trg_project_role_event_transition AFTER INSERT ON project_role_events DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_phase2_validate_role_event()"
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER trg_actor_binding_event_matches AFTER INSERT ON actor_subject_binding_events DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_phase2_validate_binding_event()"
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER trg_actor_binding_initial_event AFTER INSERT OR UPDATE ON actor_subject_bindings DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_phase2_require_binding_event()"
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER trg_actor_binding_challenge_consistency AFTER INSERT OR UPDATE ON actor_subject_bindings DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_phase2_validate_challenge_binding()"
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER trg_actor_challenge_binding_consistency AFTER INSERT OR UPDATE ON actor_enrollment_challenges DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_phase2_validate_challenge_binding()"
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER trg_bootstrap_records_first_owner AFTER INSERT ON bootstrap_records DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_phase2_validate_bootstrap()"
    )

    op.execute(
        "CREATE TRIGGER trg_membership_project_lock BEFORE INSERT OR UPDATE ON project_memberships FOR EACH ROW EXECUTE FUNCTION rb_phase2_lock_changed_project()"
    )
    op.execute(
        "CREATE TRIGGER trg_role_project_lock BEFORE INSERT OR UPDATE ON project_role_assignments FOR EACH ROW EXECUTE FUNCTION rb_phase2_lock_changed_project()"
    )
    op.execute(
        "CREATE TRIGGER trg_binding_project_lock BEFORE INSERT OR UPDATE ON actor_subject_bindings FOR EACH ROW EXECUTE FUNCTION rb_phase2_lock_changed_project()"
    )
    op.execute(
        "CREATE TRIGGER trg_actor_project_lock BEFORE UPDATE OF retired_at ON actors FOR EACH ROW EXECUTE FUNCTION rb_phase2_lock_changed_project()"
    )
    op.execute(
        "CREATE TRIGGER trg_actor_binding_human BEFORE INSERT ON actor_subject_bindings FOR EACH ROW EXECUTE FUNCTION rb_phase2_guard_human_actor()"
    )
    op.execute(
        "CREATE TRIGGER trg_actor_challenge_human BEFORE INSERT ON actor_enrollment_challenges FOR EACH ROW EXECUTE FUNCTION rb_phase2_guard_human_actor()"
    )
    op.execute(
        "CREATE TRIGGER trg_challenge_deployment_lock BEFORE INSERT ON actor_enrollment_challenges FOR EACH ROW EXECUTE FUNCTION rb_phase2_lock_deployment()"
    )
    op.execute(
        "CREATE TRIGGER trg_membership_transition BEFORE UPDATE ON project_memberships FOR EACH ROW EXECUTE FUNCTION rb_phase2_guard_membership_update()"
    )
    op.execute(
        "CREATE TRIGGER trg_role_transition BEFORE UPDATE ON project_role_assignments FOR EACH ROW EXECUTE FUNCTION rb_phase2_guard_role_update()"
    )
    op.execute(
        "CREATE TRIGGER trg_binding_transition BEFORE UPDATE ON actor_subject_bindings FOR EACH ROW EXECUTE FUNCTION rb_phase2_guard_binding_update()"
    )
    op.execute(
        "CREATE TRIGGER trg_challenge_transition BEFORE UPDATE ON actor_enrollment_challenges FOR EACH ROW EXECUTE FUNCTION rb_phase2_guard_challenge_update()"
    )
    for table in (
        "project_memberships",
        "project_role_assignments",
        "actor_subject_bindings",
        "actor_enrollment_challenges",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_no_delete BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION rb_phase2_guard_immutable()"
        )

    for table in (
        "project_memberships",
        "project_role_assignments",
        "actor_subject_bindings",
        "actors",
    ):
        op.execute(
            f"CREATE CONSTRAINT TRIGGER trg_{table}_owner_coverage AFTER INSERT OR UPDATE ON {table} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_phase2_check_owner_coverage()"
        )


def downgrade() -> None:
    bind = op.get_bind()
    rows = (
        bind.execute(
            sa.text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = ANY(:tables)"
            ),
            {"tables": list(PHASE2_TABLES)},
        )
        .scalars()
        .all()
    )
    if any(
        bind.execute(
            sa.text(f"SELECT EXISTS (SELECT 1 FROM {sa.sql.quoted_name(table, True)} LIMIT 1)")
        ).scalar_one()
        for table in rows
    ):
        raise RuntimeError("PR2-00 downgrade refused: Phase 2 canonical rows would be lost")

    op.drop_constraint(
        "fk_actor_subject_bindings_legacy_challenge",
        "actor_subject_bindings",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_actor_enrollment_challenges_result_binding",
        "actor_enrollment_challenges",
        type_="foreignkey",
    )

    for table in (
        "project_memberships",
        "project_role_assignments",
        "actor_subject_bindings",
        "actors",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_owner_coverage ON {table}")
    for table, name in (
        ("project_memberships", "trg_membership_project_lock"),
        ("project_role_assignments", "trg_role_project_lock"),
        ("actor_subject_bindings", "trg_binding_project_lock"),
        ("actors", "trg_actor_project_lock"),
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {name} ON {table}")
    for table, name in (
        ("project_membership_events", "trg_project_membership_initial_event"),
        ("project_membership_events", "trg_project_membership_event_transition"),
        ("project_role_events", "trg_project_role_event_transition"),
        ("actor_subject_binding_events", "trg_actor_binding_event_matches"),
        ("actor_subject_bindings", "trg_actor_binding_challenge_consistency"),
        ("actor_enrollment_challenges", "trg_actor_challenge_binding_consistency"),
        ("bootstrap_records", "trg_bootstrap_records_first_owner"),
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {name} ON {table}")
    for table in (
        "project_membership_events",
        "project_role_events",
        "actor_subject_binding_events",
        "bootstrap_records",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table}")

    for function in (
        "rb_phase2_validate_bootstrap()",
        "rb_phase2_require_binding_event()",
        "rb_phase2_require_role_event()",
        "rb_phase2_guard_human_actor()",
        "rb_phase2_guard_binding_update()",
        "rb_phase2_guard_role_update()",
        "rb_phase2_guard_membership_update()",
        "rb_phase2_lock_deployment()",
        "rb_phase2_validate_challenge_binding()",
        "rb_phase2_validate_binding_event()",
        "rb_phase2_validate_role_event()",
        "rb_phase2_validate_membership_event()",
        "rb_phase2_require_membership_event()",
        "rb_phase2_lock_changed_project()",
        "rb_phase2_guard_immutable()",
        "rb_phase2_guard_challenge_update()",
        "rb_phase2_check_owner_coverage()",
        "rb_phase2_owner_coverage(uuid)",
        "rb_phase2_lock_project(uuid)",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {function} CASCADE")

    for table in reversed(PHASE2_TABLES):
        op.drop_table(table)
    # btree_gist may be shared by other installed extensions or application DDL.
