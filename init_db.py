from models import Base, SessionLocal, User, Category, Poll, Vote, Admin
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def init_db():
    db = SessionLocal()
    
    try:
        # Создаем тестового админа
        if not db.query(Admin).filter(Admin.username == "admin").first():
            admin = Admin(
                username="admin",
                hashed_password=pwd_context.hash("admin123")
            )
            db.add(admin)
            db.commit()
            print("Администратор создан: логин - admin, пароль - admin123")
        
        # Создаем тестовые категории
        if not db.query(Category).first():
            categories = [
                Category(name="Политика", description="Опросы на политические темы"),
                Category(name="Технологии", description="Новые технологии и гаджеты"),
                Category(name="Спорт", description="Спортивные мероприятия")
            ]
            db.add_all(categories)
            db.commit()  # Фиксируем категории
            print("Созданы тестовые категории")
        
        # Получаем ID первой категории (после коммита)
        first_category = db.query(Category).first()
        if not first_category:
            raise Exception("Не удалось создать категории")
        
        # Создаем тестовые опросы
        if not db.query(Poll).first():
            polls = [
                Poll(question="Поддерживаете ли вы текущую политику правительства?", category_id=first_category.id),
                Poll(question="Нужно ли регулировать искусственный интеллект?", category_id=first_category.id),
                Poll(question="Следите ли вы за Олимпийскими играми?", category_id=first_category.id)
            ]
            db.add_all(polls)
            db.commit()  # Фиксируем опросы
            print("Созданы тестовые опросы")
        
        # Создаем тестового пользователя
        if not db.query(User).filter(User.username == "testuser").first():
            user = User(
                username="testuser",
                email="test@example.com",
                hashed_password=pwd_context.hash("test123")
            )
            db.add(user)
            db.commit()  # Фиксируем пользователя
            print("Создан тестовый пользователь: testuser / test123")
    
    except Exception as e:
        db.rollback()
        print(f"Ошибка: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    print("Инициализация базы данных завершена!")