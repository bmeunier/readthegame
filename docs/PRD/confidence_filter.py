"""
Filename: confidence_filter.py

Description:
    Confidence-aware segment filtering module for audio pipeline.
    Filters transcription segments based on confidence scores to improve
    downstream processing quality. Supports multiple confidence calculation
    methods and provides detailed observability.

Usage:
    from askthegame.utils.confidence_filter import ConfidenceFilter
    
    filter = ConfidenceFilter()
    passed, flagged, dropped = filter.filter_segments(segments)

Author: Benoit Meunier
Created: 2025-06-27
Last Updated: 2025-06-27
"""

import json
import logging
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional


class ConfidenceFilterConfig:
    """Configuration for confidence filtering."""
    
    def __init__(self, 
                 high_threshold: float = 0.85,
                 low_threshold: float = 0.75,
                 min_words: int = 3,
                 min_words_high_confidence: int = 2,
                 short_segment_confidence_threshold: float = 0.9,
                 max_duration: float = 30.0,
                 confidence_method: str = "average",
                 output_dir: str = "data/confidence_reports"):
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        self.min_words = min_words
        self.min_words_high_confidence = min_words_high_confidence
        self.short_segment_confidence_threshold = short_segment_confidence_threshold
        self.max_duration = max_duration
        self.confidence_method = confidence_method
        self.output_dir = output_dir
        
        # Validate configuration
        self._validate()
    
    def _validate(self):
        """Validate configuration parameters."""
        if not 0.0 <= self.low_threshold <= self.high_threshold <= 1.0:
            raise ValueError(f"Invalid thresholds: low={self.low_threshold}, high={self.high_threshold}")
        
        if self.min_words < 1:
            raise ValueError(f"min_words must be >= 1, got {self.min_words}")
        
        if self.min_words_high_confidence < 1:
            raise ValueError(f"min_words_high_confidence must be >= 1, got {self.min_words_high_confidence}")
        
        if not 0.0 <= self.short_segment_confidence_threshold <= 1.0:
            raise ValueError(f"short_segment_confidence_threshold must be between 0.0 and 1.0, got {self.short_segment_confidence_threshold}")
        
        if self.max_duration <= 0:
            raise ValueError(f"max_duration must be > 0, got {self.max_duration}")
        
        if self.confidence_method not in ["average", "weighted", "median", "percentile"]:
            raise ValueError(f"Invalid confidence_method: {self.confidence_method}")


class ConfidenceFilter:
    """Main confidence filtering class."""
    
    def __init__(self, config: Optional[ConfidenceFilterConfig] = None):
        self.config = config or ConfidenceFilterConfig()
        self.logger = logging.getLogger(__name__)
        
        # Create output directory
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
        
        # Stats for reporting
        self.stats = {
            "total_segments": 0,
            "passed": 0,
            "flagged": 0,
            "dropped": 0,
            "confidence_scores": [],
            "processing_start": None,
            "processing_duration": 0.0,
            "flagged_reasons": {},
            "dropped_reasons": {}
        }
    
    def filter_segments(self, segments: List[Dict[str, Any]], 
                       episode_id: Optional[str] = None,
                       save_results: bool = True) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Filter segments based on confidence scores.
        
        Args:
            segments: List of segments to filter
            episode_id: Optional episode identifier for output files
            save_results: Whether to save results to files
            
        Returns:
            Tuple of (passed_segments, flagged_segments, dropped_segments)
        """
        self.stats["processing_start"] = time.time()
        self.stats["total_segments"] = len(segments)
        
        passed, flagged, dropped = [], [], []
        
        try:
            for segment in segments:
                decision, reason, confidence_score = self._evaluate_segment(segment)
                
                # Add decision metadata to segment
                segment_with_meta = segment.copy()
                segment_with_meta.update({
                    "filter_decision": decision,
                    "filter_reason": reason,
                    "calculated_confidence": confidence_score,
                    "filter_timestamp": datetime.now().isoformat()
                })
                
                # Route to appropriate bucket and track reasons
                if decision == "passed":
                    passed.append(segment_with_meta)
                    self.stats["passed"] += 1
                elif decision == "flagged":
                    flagged.append(segment_with_meta)
                    self.stats["flagged"] += 1
                    # Track flagged reasons
                    self.stats["flagged_reasons"][reason] = self.stats["flagged_reasons"].get(reason, 0) + 1
                else:  # dropped
                    dropped.append(segment_with_meta)
                    self.stats["dropped"] += 1
                    # Track dropped reasons
                    self.stats["dropped_reasons"][reason] = self.stats["dropped_reasons"].get(reason, 0) + 1
                
                # Track confidence for statistics
                if confidence_score is not None:
                    self.stats["confidence_scores"].append(confidence_score)
            
            self.stats["processing_duration"] = time.time() - self.stats["processing_start"]
            
            self.logger.info(f"Filtered {len(segments)} segments: "
                           f"{len(passed)} passed, {len(flagged)} flagged, {len(dropped)} dropped")
            
            # Save results if requested
            if save_results:
                self._save_results(passed, flagged, dropped, episode_id)
            
            return passed, flagged, dropped
            
        except Exception as e:
            self.logger.error(f"Confidence filtering failed: {e}", exc_info=True)
            # Return original segments as passed on failure
            return segments, [], []
    
    def _evaluate_segment(self, segment: Dict[str, Any]) -> Tuple[str, str, Optional[float]]:
        """
        Evaluate a single segment and determine its fate.
        
        Returns:
            Tuple of (decision, reason, confidence_score)
        """
        try:
            # Extract segment data
            words = segment.get('words', [])
            start_time = segment.get('start', 0.0)
            end_time = segment.get('end', 0.0)
            duration = end_time - start_time
            
            # Edge case: Empty segments
            if not words:
                return "dropped", "empty_segment", None
            
            # Smart min_words check: Consider confidence for short segments
            word_count = len(words)
            confidence_score = self._calculate_confidence(words)
            
            if word_count < self.config.min_words:
                # Allow shorter segments if they have high confidence
                if (word_count >= self.config.min_words_high_confidence and 
                    confidence_score is not None and 
                    confidence_score >= self.config.short_segment_confidence_threshold):
                    # High confidence short segment gets a pass
                    pass  # Continue to normal confidence evaluation
                else:
                    return "flagged", "too_few_words", confidence_score
            
            # Edge case: Very long segments
            if duration > self.config.max_duration:
                return "flagged", "excessive_duration", confidence_score
            
            # Confidence score already calculated above
            
            if confidence_score is None:
                return "dropped", "no_confidence_data", None
            
            # Apply confidence thresholds
            if confidence_score >= self.config.high_threshold:
                return "passed", "high_confidence", confidence_score
            elif confidence_score >= self.config.low_threshold:
                return "flagged", "medium_confidence", confidence_score
            else:
                return "dropped", "low_confidence", confidence_score
                
        except Exception as e:
            self.logger.warning(f"Failed to evaluate segment: {e}")
            return "dropped", "evaluation_error", None
    
    def _calculate_confidence(self, words: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate confidence score based on configured method."""
        if not words:
            return None
        
        try:
            # Extract confidence scores, handling missing values
            confidences = []
            durations = []
            
            for word in words:
                conf = word.get('confidence')
                if conf is not None:
                    # Normalize malformed confidence values
                    if conf < 0:
                        conf = 0.0
                    elif conf > 1.0:
                        conf = 1.0
                    confidences.append(conf)
                    
                    # Calculate duration for weighted average
                    start = word.get('start', 0.0)
                    end = word.get('end', 0.0)
                    durations.append(max(0.01, end - start))  # Minimum duration
                else:
                    # Treat missing confidence as 0.0
                    confidences.append(0.0)
                    durations.append(0.01)
            
            if not confidences:
                return None
            
            # Calculate based on method
            if self.config.confidence_method == "average":
                return sum(confidences) / len(confidences)
            
            elif self.config.confidence_method == "weighted":
                if len(confidences) != len(durations):
                    return sum(confidences) / len(confidences)  # Fallback
                
                weighted_sum = sum(conf * dur for conf, dur in zip(confidences, durations))
                total_duration = sum(durations)
                return weighted_sum / total_duration if total_duration > 0 else 0.0
            
            elif self.config.confidence_method == "median":
                return statistics.median(confidences)
            
            elif self.config.confidence_method == "percentile":
                # Use 25th percentile to handle low-confidence outliers
                sorted_confs = sorted(confidences)
                index = int(0.25 * len(sorted_confs))
                return sorted_confs[index]
            
            else:
                # Fallback to average
                return sum(confidences) / len(confidences)
                
        except Exception as e:
            self.logger.warning(f"Confidence calculation failed: {e}")
            return None
    
    def _save_results(self, passed: List[Dict], flagged: List[Dict], 
                     dropped: List[Dict], episode_id: Optional[str]):
        """Save filtering results to files."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = f"{episode_id}_{timestamp}" if episode_id else timestamp
            
            output_dir = Path(self.config.output_dir)
            
            # Save segment lists
            with open(output_dir / f"{prefix}_segments_passed.json", 'w') as f:
                json.dump(passed, f, indent=2, ensure_ascii=False)
            
            with open(output_dir / f"{prefix}_segments_flagged.json", 'w') as f:
                json.dump(flagged, f, indent=2, ensure_ascii=False)
            
            with open(output_dir / f"{prefix}_segments_dropped.json", 'w') as f:
                json.dump(dropped, f, indent=2, ensure_ascii=False)
            
            # Save detailed report
            self._save_report(output_dir / f"{prefix}_filter_report.txt", dropped)
            
            self.logger.info(f"Confidence filtering results saved to {output_dir} with prefix {prefix}")
            
        except Exception as e:
            self.logger.error(f"Failed to save filtering results: {e}", exc_info=True)
    
    def _save_report(self, report_path: Path, dropped_samples: List[Dict]):
        """Save human-readable filtering report."""
        try:
            with open(report_path, 'w') as f:
                f.write(f"Confidence Filtering Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n")
                f.write(f"Processing Duration: {self.stats['processing_duration']:.1f}s\n")
                f.write(f"Total Segments: {self.stats['total_segments']:,}\n\n")
                
                f.write("RESULTS:\n")
                total = self.stats['total_segments']
                if total > 0:
                    f.write(f"- Passed: {self.stats['passed']} ({100*self.stats['passed']/total:.1f}%)\n")
                    f.write(f"- Flagged: {self.stats['flagged']} ({100*self.stats['flagged']/total:.1f}%)\n")
                    f.write(f"- Dropped: {self.stats['dropped']} ({100*self.stats['dropped']/total:.1f}%)\n\n")
                
                # Confidence statistics
                if self.stats['confidence_scores']:
                    scores = self.stats['confidence_scores']
                    f.write("CONFIDENCE STATISTICS:\n")
                    f.write(f"- Mean: {statistics.mean(scores):.3f}\n")
                    f.write(f"- Median: {statistics.median(scores):.3f}\n")
                    f.write(f"- 25th percentile: {statistics.quantiles(scores, n=4)[0]:.3f}\n")
                    f.write(f"- 75th percentile: {statistics.quantiles(scores, n=4)[2]:.3f}\n\n")
                
                # Configuration used
                f.write("THRESHOLDS USED:\n")
                f.write(f"- High: {self.config.high_threshold}\n")
                f.write(f"- Low: {self.config.low_threshold}\n")
                f.write(f"- Min words: {self.config.min_words}\n")
                f.write(f"- Min words (high conf): {self.config.min_words_high_confidence}\n")
                f.write(f"- Short segment threshold: {self.config.short_segment_confidence_threshold}\n")
                f.write(f"- Max duration: {self.config.max_duration}s\n")
                f.write(f"- Method: {self.config.confidence_method}\n\n")
                
                # Flagged reason breakdown
                if self.stats['flagged_reasons']:
                    f.write("FLAGGED REASONS:\n")
                    for reason, count in sorted(self.stats['flagged_reasons'].items(), 
                                               key=lambda x: x[1], reverse=True):
                        f.write(f"- {reason}: {count}\n")
                    f.write("\n")
                
                # Dropped reason breakdown
                if self.stats['dropped_reasons']:
                    f.write("DROPPED REASONS:\n")
                    for reason, count in sorted(self.stats['dropped_reasons'].items(), 
                                               key=lambda x: x[1], reverse=True):
                        f.write(f"- {reason}: {count}\n")
                    f.write("\n")
                
                # Sample dropped segments
                if dropped_samples:
                    f.write("SAMPLE DROPPED SEGMENTS:\n")
                    for i, segment in enumerate(dropped_samples[:5]):  # Show first 5
                        start_time = segment.get('start', 0)
                        transcript = segment.get('transcript', '')[:50]
                        confidence = segment.get('calculated_confidence', 0)
                        mins, secs = divmod(int(start_time), 60)
                        f.write(f"- [{mins:02d}:{secs:02d}] \"{transcript}...\" (conf: {confidence:.2f})\n")
                    f.write("\n")
                
                # Tuning hints
                f.write("TUNING HINTS:\n")
                drop_rate = self.stats['dropped'] / total if total > 0 else 0
                if drop_rate > 0.15:
                    f.write("- Consider lowering thresholds if >15% dropped\n")
                f.write("- Review flagged segments for pattern analysis\n")
                
        except Exception as e:
            self.logger.error(f"Failed to save report: {e}", exc_info=True)