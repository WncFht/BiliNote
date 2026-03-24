import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.staticfiles import StaticFiles

from app import create_app
from app.db.init_db import init_db
from app.db.provider_dao import seed_default_providers
from app.exceptions.exception_handlers import register_exception_handlers
from app.runtime_config import initialize_backend_runtime
from app.services.transcriber_config_manager import TranscriberConfigManager
from app.utils.logger import get_logger
from events import register_handler

logger = get_logger(__name__)
load_dotenv()

static_path = os.getenv('STATIC', '/static')
out_dir = os.getenv('OUT_DIR', './static/screenshots')

static_dir = 'static'
uploads_dir = 'uploads'
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)
if not os.path.exists(out_dir):
    os.makedirs(out_dir)


@asynccontextmanager
async def lifespan(app: FastAPI):
    register_handler()
    initialize_backend_runtime()
    init_db()
    seed_default_providers()
    config = TranscriberConfigManager().get_config()
    logger.info(
        "当前转写器配置: type=%s, model_size=%s",
        config['transcriber_type'],
        config['whisper_model_size'],
    )
    yield


app = create_app(lifespan=lifespan)
origins = [
    'http://localhost',
    'http://127.0.0.1',
    'http://tauri.localhost',
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
register_exception_handlers(app)
app.mount(static_path, StaticFiles(directory=static_dir), name='static')
app.mount('/uploads', StaticFiles(directory=uploads_dir), name='uploads')


if __name__ == '__main__':
    port = int(os.getenv('BACKEND_PORT', 8483))
    host = os.getenv('BACKEND_HOST', '0.0.0.0')
    logger.info(f'Starting server on {host}:{port}')
    uvicorn.run(app, host=host, port=port, reload=False)
