"""Verify all project requirements are met."""
from db import get_db

print("=== CHECKLIST VERIFICATION ===")
print()

with get_db() as conn:
    with conn.cursor() as cur:
        # 1. Check 6 tables exist
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
        tables = [r[0] for r in cur.fetchall()]
        print(f"1. Tables ({len(tables)}): {tables}")

        # 2. Check view exists
        cur.execute("SELECT table_name FROM information_schema.views WHERE table_schema='public'")
        views = [r[0] for r in cur.fetchall()]
        print(f"2. Views: {views}")

        # 3. Check triggers
        cur.execute("SELECT trigger_name FROM information_schema.triggers WHERE trigger_schema='public'")
        triggers = [r[0] for r in cur.fetchall()]
        print(f"3. Triggers: {triggers}")

        # 4. Check functions/procedures
        cur.execute("SELECT routine_name, routine_type FROM information_schema.routines WHERE routine_schema='public'")
        routines = [(r[0], r[1]) for r in cur.fetchall()]
        print(f"4. Functions/Procedures: {routines}")

        # 5. Check indexes
        cur.execute("SELECT indexname FROM pg_indexes WHERE schemaname='public' AND indexname LIKE 'idx_%'")
        indexes = [r[0] for r in cur.fetchall()]
        print(f"5. Custom Indexes: {indexes}")

        # 6. Check sample data
        cur.execute("SELECT COUNT(*) FROM users")
        print(f"6. Users: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM experiments")
        print(f"7. Experiments: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM runs")
        print(f"8. Runs: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM metrics")
        print(f"9. Metrics: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM hyperparameters")
        print(f"10. Hyperparameters: {cur.fetchone()[0]}")

        # 7. Check image URLs
        cur.execute("SELECT id, image_url FROM runs ORDER BY id")
        for row in cur.fetchall():
            tag = "Firebase" if row[1] and "firebase" in str(row[1]).lower() else "LOCAL/NULL"
            print(f"11. Run {row[0]} image: {tag} -> {str(row[1])[:80]}")

        # 8. Check leaderboard view works
        cur.execute("SELECT COUNT(*) FROM leaderboard_view")
        print(f"12. Leaderboard view rows: {cur.fetchone()[0]}")

        # 9. Test function
        cur.execute("SELECT get_best_run(1)")
        print(f"13. get_best_run(1) = {cur.fetchone()[0]}")

print()
print("=== FIREBASE CHECK ===")
import firebase_admin
from firebase_admin import db as rtdb
from firebase_helper import init_firebase
init_firebase()
ref = rtdb.reference("runs")
data = ref.get()
if data:
    print(f"14. Firebase RTDB /runs has {len(data)} entries")
    for k, v in data.items():
        print(f"    /runs/{k}: {v}")
else:
    print("14. Firebase RTDB /runs is empty")

print()
print("=== ALL CHECKS COMPLETE ===")
