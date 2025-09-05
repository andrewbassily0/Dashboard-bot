#!/bin/bash

case "$1" in
    start)
        echo "🚀 Starting the bot..."
        if pgrep -f "run_telegram_bot" > /dev/null; then
            echo "❌ Bot is already running!"
            exit 1
        fi
        docker-compose exec -T django_app bash -c "cd /app && python3 manage.py run_telegram_bot" &
        echo "✅ Bot started successfully!"
        ;;
    stop)
        echo "🛑 Stopping the bot..."
        pkill -f "run_telegram_bot"
        pkill -f "manage_bot"
        echo "✅ Bot stopped"
        ;;
    status)
        echo "🔍 Checking bot status..."
        if pgrep -f "run_telegram_bot" > /dev/null; then
            instances=$(pgrep -f "run_telegram_bot" | wc -l)
            echo "✅ Bot is running ($instances instances)"
            ps aux | grep "run_telegram_bot" | grep -v grep
        else
            echo "❌ Bot is stopped"
        fi
        ;;
    restart)
        echo "🔄 Restarting the bot..."
        $0 stop
        sleep 3
        $0 start
        ;;
    logs)
        echo "📋 Showing bot logs..."
        docker-compose logs django_app --tail=20
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart|logs}"
        echo ""
        echo "start   - Start the bot"
        echo "stop    - Stop the bot"  
        echo "status  - Check bot status"
        echo "restart - Restart the bot"
        echo "logs    - Show bot logs"
        exit 1
        ;;
esac 