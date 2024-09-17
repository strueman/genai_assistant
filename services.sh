   #!/bin/bash

   start() {
       . /opt/homebrew/anaconda3/bin/activate && conda activate /opt/homebrew/anaconda3/envs/assistant && \
       /opt/homebrew/anaconda3/envs/assistant/bin/python /Users/simon/dev_projects/gen-ai/cache_server.py > /Users/simon/dev_projects/gen-ai/cache_server.log 2>&1 &

       . /opt/homebrew/anaconda3/bin/activate && conda activate /opt/homebrew/anaconda3/envs/assistant && \
       /opt/homebrew/anaconda3/envs/assistant/bin/python /Users/simon/dev_projects/gen-ai/rss_feeds.py > /Users/simon/dev_projects/gen-ai/rss_feeds.log 2>&1 &


       # Note: Both commands now run in the background with '&' at the end
   }

   stop() {
        pkill -f rss_feeds.py
        pkill -f cache_server.py
    #    kill $(cat /tmp/rss_feeds.pid)
    #    rm /tmp/rss_feeds.pid
   }

   case "$1" in 
       start)   start ;;
       stop)    stop ;;
       restart) stop; start ;;
       *) echo "usage: $0 start|stop|restart" >&2
          exit 1
          ;;
   esac


    # ./manage_rss_feeds.sh start
    # ./manage_rss_feeds.sh stop
    # ./manage_rss_feeds.sh restart

    #  pkill -f rss_feeds.py
    #  ps aux | grep rss_feeds.py
