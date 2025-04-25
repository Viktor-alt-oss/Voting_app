from models import Base, engine

def recreate_db():
    # Удаляем все таблицы
    Base.metadata.drop_all(engine)
    # Создаём заново
    Base.metadata.create_all(engine)
    print("База данных успешно пересоздана!")

if __name__ == "__main__":
    recreate_db()