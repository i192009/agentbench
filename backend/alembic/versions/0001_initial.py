"""Initial schema and database-enforced immutable snapshot guards."""

from agentbench.database import Base
from alembic import op

revision = "0001"
down_revision = None


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    if bind.dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION ab_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'historical snapshots are immutable'; END; $$""")
        op.execute(
            "CREATE TRIGGER immutable_agents BEFORE UPDATE OR DELETE ON agent_versions FOR EACH ROW EXECUTE FUNCTION ab_immutable()"
        )
        op.execute("""CREATE FUNCTION ab_frozen() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN IF OLD.frozen THEN RAISE EXCEPTION 'frozen dataset is immutable'; END IF; RETURN NEW; END; $$""")
        op.execute(
            "CREATE TRIGGER immutable_datasets BEFORE UPDATE OR DELETE ON dataset_versions FOR EACH ROW EXECUTE FUNCTION ab_frozen()"
        )
        op.execute("""CREATE FUNCTION ab_frozen_case() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN IF EXISTS (SELECT 1 FROM dataset_versions WHERE id=COALESCE(NEW.version_id,OLD.version_id) AND frozen)
        THEN RAISE EXCEPTION 'frozen dataset cases are immutable'; END IF; RETURN COALESCE(NEW,OLD); END; $$""")
        op.execute(
            "CREATE TRIGGER immutable_cases BEFORE INSERT OR UPDATE OR DELETE ON test_cases FOR EACH ROW EXECUTE FUNCTION ab_frozen_case()"
        )
    else:
        op.execute(
            "CREATE TRIGGER immutable_agents BEFORE UPDATE ON agent_versions BEGIN SELECT RAISE(ABORT, 'immutable agent version'); END"
        )
        op.execute(
            "CREATE TRIGGER immutable_datasets BEFORE UPDATE ON dataset_versions WHEN OLD.frozen=1 BEGIN SELECT RAISE(ABORT, 'frozen dataset'); END"
        )
        for operation in ["INSERT", "UPDATE", "DELETE"]:
            reference = "OLD" if operation == "DELETE" else "NEW"
            op.execute(
                f"CREATE TRIGGER immutable_cases_{operation.lower()} BEFORE {operation} ON test_cases WHEN (SELECT frozen FROM dataset_versions WHERE id={reference}.version_id)=1 BEGIN SELECT RAISE(ABORT, 'frozen cases'); END"
            )


def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
    if op.get_bind().dialect.name == "postgresql":
        for name in ["ab_immutable", "ab_frozen", "ab_frozen_case"]:
            op.execute(f"DROP FUNCTION IF EXISTS {name}() CASCADE")
