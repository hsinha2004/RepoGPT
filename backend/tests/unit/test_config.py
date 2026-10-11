from app.core.config import Settings


def test_settings_default_values():
    settings = Settings()
    assert settings.APP_NAME == "RepoGPT"
    assert settings.JWT_ACCESS_TTL_MINUTES == 15
    assert settings.REFRESH_TTL_DAYS == 7
    assert settings.ROUTER_MODE == "hybrid"
    assert settings.RETRIEVAL_CANDIDATES == 50
    assert len(settings.cors_origins_list) >= 1


def test_settings_mongo_uri_fallback():
    settings = Settings(
        MONGODB_URI=None,
        MONGO_APP_USER="testuser",
        MONGO_APP_PASSWORD="testpass",
        MONGO_HOST="localhost",
        MONGO_PORT=27017,
        MONGODB_DB="testdb",
    )
    uri = settings.get_mongodb_uri()
    assert "mongodb://testuser:testpass@localhost:27017/testdb?authSource=testdb" == uri


def test_settings_redis_url_generation():
    settings = Settings(
        REDIS_URL=None,
        REDIS_PASSWORD="secretredis",
        REDIS_HOST="127.0.0.1",
        REDIS_PORT=6379,
    )
    url0 = settings.get_redis_url(db=0)
    url1 = settings.get_redis_url(db=1)
    assert url0 == "redis://:secretredis@127.0.0.1:6379/0"
    assert url1 == "redis://:secretredis@127.0.0.1:6379/1"
