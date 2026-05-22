import logging.config
import colorlog

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'colored': {
            '()': colorlog.ColoredFormatter,  # 关键：使用 colorlog 的 formatter
            'format': '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'log_colors': {
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        },
        'plain': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        }
    },
    'handlers': {
        'console_colored': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'colored',
        },
        'file_plain': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'plain',
            'filename': 'app.log',
            'maxBytes': 10*1024*1024,
            'backupCount': 5,
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console_colored', 'file_plain']
    }
}

def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)
    return logging.getLogger("app")



log = setup_logging()