"""Protect run configurations and SQLite deletion of frozen histories."""

from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION ab_run_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN IF NEW.snapshot::jsonb IS DISTINCT FROM OLD.snapshot::jsonb THEN
        RAISE EXCEPTION 'run snapshots are immutable'; END IF; RETURN NEW; END; $$""")
        op.execute(
            "CREATE TRIGGER immutable_run_snapshot BEFORE UPDATE ON evaluation_runs FOR EACH ROW EXECUTE FUNCTION ab_run_snapshot()"
        )
    else:
        op.execute(
            "CREATE TRIGGER immutable_run_snapshot BEFORE UPDATE OF snapshot ON evaluation_runs WHEN NEW.snapshot <> OLD.snapshot BEGIN SELECT RAISE(ABORT,'immutable run snapshot'); END"
        )
        op.execute(
            "CREATE TRIGGER immutable_agents_delete BEFORE DELETE ON agent_versions BEGIN SELECT RAISE(ABORT,'immutable agent version'); END"
        )
        op.execute(
            "CREATE TRIGGER immutable_dataset_delete BEFORE DELETE ON dataset_versions WHEN OLD.frozen=1 BEGIN SELECT RAISE(ABORT,'frozen dataset'); END"
        )


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER immutable_run_snapshot ON evaluation_runs")
        op.execute("DROP FUNCTION ab_run_snapshot()")
    else:
        for name in ["immutable_run_snapshot", "immutable_agents_delete", "immutable_dataset_delete"]:
            op.execute(f"DROP TRIGGER {name}")
