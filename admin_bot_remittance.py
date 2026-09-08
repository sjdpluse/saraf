import logging

from telegram import Update

import keyboards
from admin_bot import build_admin_application
from services.remittance_admin import register, remittance_keyboard

# Bridge used by remittance_service.notify_admins without changing the legacy keyboard module.
keyboards.admin_remittance_keyboard = remittance_keyboard

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    app = build_admin_application()
    register(app)
    logger.info("ربات مدیریت Saraf + حواله در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
