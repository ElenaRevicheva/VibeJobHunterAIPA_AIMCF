"""Save and resume progress for batch operations"""
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class ProgressSaver:
    """Save and restore progress for long-running operations"""
    
    def __init__(self, progress_file: Path):
        self.progress_file = progress_file
        self.progress_file.parent.mkdir(exist_ok=True, parents=True)
    
    def save_progress(self, data: Dict[str, Any]):
        """Save current progress"""
        data['last_updated'] = datetime.now().isoformat()
        
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save progress: {e}")
    
    def load_progress(self) -> Dict[str, Any]:
        """Load saved progress"""
        if not self.progress_file.exists():
            return {}
        
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def clear_progress(self):
        """Clear saved progress"""
        if self.progress_file.exists():
            try:
                self.progress_file.unlink()
            except Exception:
                pass


class BatchProgressTracker:
    """Track progress for batch apply operations"""
    
    def __init__(self, save_dir: Path):
        self.saver = ProgressSaver(save_dir / "batch_progress.json")
    
    def start_batch(self, urls: List[str], session_id: str):
        """Start a new batch session"""
        self.saver.save_progress({
            'session_id': session_id,
            'total_jobs': len(urls),
            'urls': urls,
            'completed_urls': [],
            'failed_urls': [],
            'status': 'in_progress'
        })
    
    def mark_completed(self, url: str):
        """Mark a job as completed"""
        progress = self.saver.load_progress()
        if 'completed_urls' not in progress:
            progress['completed_urls'] = []
        progress['completed_urls'].append(url)
        self.saver.save_progress(progress)
    
    def mark_failed(self, url: str, error: str):
        """Mark a job as failed"""
        progress = self.saver.load_progress()
        if 'failed_urls' not in progress:
            progress['failed_urls'] = []
        progress['failed_urls'].append({'url': url, 'error': error})
        self.saver.save_progress(progress)
    
    def finish_batch(self):
        """Mark batch as complete"""
        progress = self.saver.load_progress()
        progress['status'] = 'completed'
        self.saver.save_progress(progress)
    
    def can_resume(self) -> bool:
        """Check if there's a resumable session"""
        progress = self.saver.load_progress()
        return progress.get('status') == 'in_progress'
    
    def get_remaining_urls(self) -> List[str]:
        """Get URLs that haven't been processed"""
        progress = self.saver.load_progress()
        all_urls = progress.get('urls', [])
        completed = progress.get('completed_urls', [])
        failed = [f['url'] for f in progress.get('failed_urls', [])]
        processed = set(completed + failed)
        
        return [url for url in all_urls if url not in processed]
