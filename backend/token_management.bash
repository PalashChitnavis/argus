cd ~/Documents/GitHub/argus/argus-backend
source venv/bin/activate
python3 - <<'PY'
from app.db import SessionLocal
from app.models import EnrollmentToken
s = SessionLocal()
for t in s.query(EnrollmentToken).all():
    print("TOKEN:", t.token)
    print("  used:", t.used)
    print("  used_by_node_id:", t.used_by_node_id)
    print("  used_at:", t.used_at)
    print()
s.close()
PY


cd ~/Documents/GitHub/argus/argus-backend
source venv/bin/activate
python3 - <<'PY'
from app.db import SessionLocal
from app.models import EnrollmentToken
s = SessionLocal()
deleted = s.query(EnrollmentToken).delete()
s.commit()
print(f"Deleted {deleted} tokens")
s.close()
PY

cd ~/Documents/GitHub/argus/argus-backend
source venv/bin/activate
python generate_token.py


cd /home/palash/Documents/GitHub/argus/backend && source venv/bin/activate && python3 - <<'PY'
from app.db import engine, Base
import app.models  # Keeps models imported so metadata recognizes them
from sqlalchemy.schema import DropTable
from sqlalchemy.ext.compiler import compiles

# Force PostgreSQL to drop tables using CASCADE
@compiles(DropTable, "postgresql")
def _compile_drop_table(element, compiler, **kwargs):
    return compiler.visit_drop_table(element) + " CASCADE"

# Drop and recreate
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

print('Successfully dropped and recreated all tables with CASCADE!')
PY

fastapi dev ./app/main.py