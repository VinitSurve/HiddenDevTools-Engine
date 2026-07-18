import datetime
from scheduler.content_selector import ContentSelector
from scheduler.state_manager import StateManager
from scheduler.queue import PublishingQueue
from scheduler.publisher import Publisher

class DailyPipeline:
    def __init__(self):
        self.state_manager = StateManager()
        self.queue = PublishingQueue()
        self.publisher = Publisher(self.queue)

    def run_today(self, override_day=None):
        today_date = datetime.datetime.now().strftime("%Y-%m-%d")
        niche = ContentSelector.get_todays_niche(override_day=override_day)
        
        if not niche:
            print(f"No niche scheduled for today ({today_date}). Exiting.")
            return
            
        print(f"[{today_date}] Starting pipeline for niche: {niche}")
        batch_id = self.state_manager.record_batch_start(today_date, niche)
        
        try:
            # 1. Read today's content from Google Sheets
            # data = sheet_service.read_today(niche)
            
            # 2. Validate row
            # validate(data)
            
            # 3. Generate PNGs
            # files = renderers[niche].render(data, out_dir)
            
            # 4. Generate Caption
            # caption = caption_service.generate(data)
            
            # 5. Move row -> Published (Sheet update)
            # sheet_service.mark_published(data)
            
            # 6. Save output/
            # storage_service.upload(files)
            
            # 7. Queue post
            self.queue.enqueue({
                "id": f"batch_{batch_id}",
                "niche": niche,
                # "files": files,
                # "caption": caption
            })
            
            # 8. Meta Business Suite Scheduler
            self.publisher.publish_pending()
            
            self.state_manager.update_batch_status(batch_id, "COMPLETED")
            print("Pipeline completed successfully.")
            
        except Exception as e:
            self.state_manager.update_batch_status(batch_id, "FAILED")
            print(f"Pipeline failed: {e}")
