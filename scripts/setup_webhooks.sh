#!/bin/bash
# Script to register webhooks for Telegram and Discord
    #!/bin/bash

    # Exit immediately if a command exits with a non-zero status.
    set -e

    # IMPORTANT: Replace with your actual Telegram Bot Token
    TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
    # IMPORTANT: Replace with your ngrok HTTPS URL (e.g., from running 'ngrok http 8000')
    # Make sure 'ngrok http 8000' is running in a separate terminal and provides an HTTPS URL.
    NGROK_URL="YOUR_NGROK_HTTPS_URL"

    WEBHOOK_URL="${NGROK_URL}/telegram/webhook"

    echo "Setting Telegram webhook to: ${WEBHOOK_URL}"
    # Use curl to call Telegram's setWebhook API
    curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=${WEBHOOK_URL}"

    echo ""
    echo "To get current webhook info: curl https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
    echo "To delete webhook: curl https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/deleteWebhook"
    