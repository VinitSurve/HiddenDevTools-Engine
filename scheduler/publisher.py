class Publisher:
    def __init__(self, queue):
        self.queue = queue

    def publish_pending(self):
        \"\"\"
        Iterates over the queue and sends to Meta Business Suite.
        \"\"\"
        pending = self.queue.get_pending()
        for post in pending:
            # Integration with Meta Business Suite goes here
            # using services.instagram_service etc.
            print(f"Publishing {post.get('niche')} post via Meta Business Suite...")
            # If successful:
            self.queue.mark_published(post.get("id"))
