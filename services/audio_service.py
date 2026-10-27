import os
import logging
import subprocess

logger = logging.getLogger(__name__)

class AudioService:
    """
    Service for handling audio manipulation and embedding.
    Prepares the pipeline for Instagram Reels by allowing Original Audio
    to be embedded into a video file before upload.
    """
    
    @staticmethod
    def embed_audio(video_path: str, audio_path: str, output_path: str) -> bool:
        """
        Embeds an audio file into a video file using ffmpeg.
        Replaces any existing audio stream in the video.
        
        Args:
            video_path: Path to the source video (e.g., .mp4)
            audio_path: Path to the source audio (e.g., .mp3, .wav)
            output_path: Path where the resulting video should be saved
            
        Returns:
            bool: True if successful, False otherwise.
        """
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return False
            
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return False
            
        # Command to replace audio:
        # -i video -i audio -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 -shortest output
        command = [
            "ffmpeg",
            "-y", # overwrite output file if it exists
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path
        ]
        
        logger.info(f"Embedding audio into video {video_path} -> {output_path}")
        
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg audio embedding failed:\n{result.stderr}")
                return False
                
            logger.info("Audio embedding successful.")
            return True
            
        except FileNotFoundError:
            logger.error("ffmpeg is not installed or not in PATH.")
            return False
        except Exception as e:
            logger.error(f"Error during audio embedding: {e}")
            return False
