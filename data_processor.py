import csv
import json
import logging
import math
import os
import re
from collections import Counter

# Configure logging
logger = logging.getLogger(__name__)


class DataProcessor:
    """
    Data processor for handling large datasets and text analysis.
    """

    def __init__(self, cache_dir="data_cache"):
        """
        Initialize the Data Processor.

        Args:
            cache_dir (str): Directory to store cached data
        """
        self.cache_dir = cache_dir

        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)

    def analyze_text(self, text):
        """
        Analyze text for basic statistics and information.

        Args:
            text (str): Text to analyze

        Returns:
            dict: Analysis results
        """
        # Basic text statistics
        words = re.findall(r"\b\w+\b", text.lower())
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Word frequency
        word_freq = Counter(words)
        most_common = word_freq.most_common(10)

        # Calculate readability scores
        readability = self._calculate_readability(text, words, sentences)

        # Sentiment analysis (simplified)
        sentiment = self._simple_sentiment_analysis(text)

        return {
            "word_count": len(words),
            "sentence_count": len(sentences),
            "character_count": len(text),
            "average_word_length": (
                sum(len(word) for word in words) / len(words) if words else 0
            ),
            "average_sentence_length": len(words) / len(sentences) if sentences else 0,
            "most_common_words": most_common,
            "readability": readability,
            "sentiment": sentiment,
        }

    def process_large_text(self, text, chunk_size=10000):
        """
        Process large text by breaking it into manageable chunks.

        Args:
            text (str): Large text to process
            chunk_size (int): Size of each chunk

        Returns:
            dict: Aggregated results
        """
        if len(text) <= chunk_size:
            return self.analyze_text(text)

        # Split text into chunks
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunks.append(text[i : i + chunk_size])

        # Process each chunk
        results = []
        for chunk in chunks:
            results.append(self.analyze_text(chunk))

        # Aggregate results
        aggregated = {
            "word_count": sum(r["word_count"] for r in results),
            "sentence_count": sum(r["sentence_count"] for r in results),
            "character_count": sum(r["character_count"] for r in results),
            "average_word_length": (
                sum(r["average_word_length"] * r["word_count"] for r in results)
                / sum(r["word_count"] for r in results)
                if any(r["word_count"] for r in results)
                else 0
            ),
            "average_sentence_length": (
                sum(r["word_count"] for r in results)
                / sum(r["sentence_count"] for r in results)
                if any(r["sentence_count"] for r in results)
                else 0
            ),
            "readability": {
                "flesch_reading_ease": (
                    sum(
                        r["readability"]["flesch_reading_ease"] * r["word_count"]
                        for r in results
                    )
                    / sum(r["word_count"] for r in results)
                    if any(r["word_count"] for r in results)
                    else 0
                ),
                "flesch_kincaid_grade": (
                    sum(
                        r["readability"]["flesch_kincaid_grade"] * r["word_count"]
                        for r in results
                    )
                    / sum(r["word_count"] for r in results)
                    if any(r["word_count"] for r in results)
                    else 0
                ),
            },
            "sentiment": {
                "positive": (
                    sum(r["sentiment"]["positive"] * r["word_count"] for r in results)
                    / sum(r["word_count"] for r in results)
                    if any(r["word_count"] for r in results)
                    else 0
                ),
                "negative": (
                    sum(r["sentiment"]["negative"] * r["word_count"] for r in results)
                    / sum(r["word_count"] for r in results)
                    if any(r["word_count"] for r in results)
                    else 0
                ),
                "overall": (
                    sum(r["sentiment"]["overall"] * r["word_count"] for r in results)
                    / sum(r["word_count"] for r in results)
                    if any(r["word_count"] for r in results)
                    else 0
                ),
            },
        }

        # Aggregate most common words
        all_words = []
        for result in results:
            all_words.extend([word for word, count in result["most_common_words"]])

        word_freq = Counter(all_words)
        aggregated["most_common_words"] = word_freq.most_common(10)

        return aggregated

    def parse_csv(self, csv_data, delimiter=",", has_header=True):
        """
        Parse CSV data into structured format.

        Args:
            csv_data (str): CSV data as string
            delimiter (str): CSV delimiter
            has_header (bool): Whether CSV has a header row

        Returns:
            dict: Parsed data and statistics
        """
        try:
            lines = csv_data.strip().split("\n")
            reader = csv.reader(lines, delimiter=delimiter)

            data = list(reader)

            if not data:
                return {"status": "error", "message": "No data found in CSV"}

            if has_header:
                header = data[0]
                rows = data[1:]
            else:
                header = [f"Column{i+1}" for i in range(len(data[0]))]
                rows = data

            # Generate statistics for each column
            column_stats = {}
            for i, col_name in enumerate(header):
                col_values = [row[i] for row in rows if i < len(row)]

                # Try to convert to numbers for numeric statistics
                numeric_values = []
                for val in col_values:
                    try:
                        numeric_values.append(float(val))
                    except (ValueError, TypeError):
                        pass

                if numeric_values:
                    column_stats[col_name] = {
                        "type": "numeric",
                        "count": len(numeric_values),
                        "min": min(numeric_values),
                        "max": max(numeric_values),
                        "mean": sum(numeric_values) / len(numeric_values),
                        "median": sorted(numeric_values)[len(numeric_values) // 2],
                        "most_common": Counter(col_values).most_common(3),
                    }
                else:
                    column_stats[col_name] = {
                        "type": "text",
                        "count": len(col_values),
                        "unique_values": len(set(col_values)),
                        "most_common": Counter(col_values).most_common(3),
                    }

            return {
                "status": "success",
                "header": header,
                "rows": rows[:100],  # Return only first 100 rows to avoid overwhelming
                "total_rows": len(rows),
                "columns": len(header),
                "column_statistics": column_stats,
                "has_header": has_header,
            }

        except Exception as e:
            logger.error(f"Error parsing CSV: {str(e)}")
            return {"status": "error", "message": f"Error parsing CSV: {str(e)}"}

    def parse_json(self, json_data):
        """
        Parse JSON data and provide analysis.

        Args:
            json_data (str): JSON data as string

        Returns:
            dict: Parsed data and statistics
        """
        try:
            data = json.loads(json_data)

            # Analyze structure
            if isinstance(data, list):
                structure = {
                    "type": "array",
                    "length": len(data),
                    "example": data[0] if data else None,
                }

                # If the array contains objects, analyze their structure
                if data and isinstance(data[0], dict):
                    common_keys = set(data[0].keys())
                    for item in data[1:10]:  # Check first 10 items
                        if isinstance(item, dict):
                            common_keys &= set(item.keys())

                    structure["common_keys"] = list(common_keys)

                    # If all objects have common keys, provide stats for each key
                    if common_keys:
                        key_stats = {}
                        for key in common_keys:
                            values = [item[key] for item in data[:100] if key in item]
                            key_stats[key] = self._analyze_json_values(values)

                        structure["key_statistics"] = key_stats

            elif isinstance(data, dict):
                structure = {
                    "type": "object",
                    "keys": list(data.keys()),
                    "key_count": len(data.keys()),
                }

                # Analyze values for each key
                key_stats = {}
                for key, value in data.items():
                    if isinstance(value, list):
                        key_stats[key] = {
                            "type": "array",
                            "length": len(value),
                            "example": value[0] if value else None,
                        }
                    elif isinstance(value, dict):
                        key_stats[key] = {
                            "type": "object",
                            "keys": list(value.keys()),
                            "key_count": len(value.keys()),
                        }
                    else:
                        key_stats[key] = {"type": type(value).__name__, "value": value}

                structure["value_statistics"] = key_stats

            else:
                structure = {"type": type(data).__name__, "value": data}

            return {
                "status": "success",
                "structure": structure,
                "sample": (
                    data
                    if not isinstance(data, (list, dict))
                    or len(json.dumps(data)) < 1000
                    else "(data too large for sample)"
                ),
            }

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON: {str(e)}")
            return {"status": "error", "message": f"Invalid JSON: {str(e)}"}
        except Exception as e:
            logger.error(f"Error analyzing JSON: {str(e)}")
            return {"status": "error", "message": f"Error analyzing JSON: {str(e)}"}

    def calculate_expressions(self, expressions):
        """
        Calculate mathematical expressions.

        Args:
            expressions (list): List of mathematical expressions as strings

        Returns:
            list: Results for each expression
        """
        results = []

        for expr in expressions:
            try:
                # Remove any unsafe code
                sanitized = self._sanitize_math_expression(expr)

                # Calculate the expression
                result = eval(
                    sanitized,
                    {"__builtins__": {}},
                    {
                        "abs": abs,
                        "max": max,
                        "min": min,
                        "pow": pow,
                        "round": round,
                        "sum": sum,
                        "len": len,
                        "sqrt": math.sqrt,
                        "log": math.log,
                        "log10": math.log10,
                        "sin": math.sin,
                        "cos": math.cos,
                        "tan": math.tan,
                        "pi": math.pi,
                        "e": math.e,
                    },
                )

                results.append(
                    {"expression": expr, "result": result, "status": "success"}
                )

            except Exception as e:
                results.append({"expression": expr, "error": str(e), "status": "error"})

        return results

    def summarize_text(self, text, max_sentences=5):
        """
        Generate a simple summary of the text by extracting key sentences.

        Args:
            text (str): Text to summarize
            max_sentences (int): Maximum number of sentences in summary

        Returns:
            dict: Summary results
        """
        # Split into sentences
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return {"status": "error", "message": "No sentences found in text"}

        if len(sentences) <= max_sentences:
            return {
                "status": "success",
                "summary": text,
                "sentence_count": len(sentences),
                "character_count": len(text),
            }

        # Calculate sentence scores using a simplified version of TextRank
        word_frequencies = self._get_word_frequencies(text)
        sentence_scores = {}

        for i, sentence in enumerate(sentences):
            words = re.findall(r"\b\w+\b", sentence.lower())
            score = (
                sum(word_frequencies.get(word, 0) for word in words) / len(words)
                if words
                else 0
            )
            sentence_scores[i] = score

        # Select top sentences
        top_indices = sorted(
            sentence_scores.keys(), key=lambda i: sentence_scores[i], reverse=True
        )[:max_sentences]
        top_indices.sort()  # Sort by original order

        summary_sentences = [sentences[i] for i in top_indices]
        summary = ". ".join(summary_sentences) + "."

        return {
            "status": "success",
            "summary": summary,
            "original_sentences": len(sentences),
            "summary_sentences": len(summary_sentences),
            "compression_ratio": len(summary) / len(text),
        }

    def _get_word_frequencies(self, text):
        """
        Calculate word frequencies for text summarization.

        Args:
            text (str): Input text

        Returns:
            dict: Word frequencies
        """
        # Remove common stop words
        stop_words = {
            "a",
            "an",
            "the",
            "and",
            "or",
            "but",
            "is",
            "are",
            "was",
            "were",
            "in",
            "on",
            "at",
            "to",
            "for",
            "with",
            "by",
            "about",
            "of",
            "from",
        }

        words = re.findall(r"\b\w+\b", text.lower())
        word_freq = {}

        for word in words:
            if word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Normalize frequencies
        max_freq = max(word_freq.values()) if word_freq else 1
        word_freq = {word: freq / max_freq for word, freq in word_freq.items()}

        return word_freq

    def _calculate_readability(self, text, words, sentences):
        """
        Calculate readability scores for text.

        Args:
            text (str): Text to analyze
            words (list): List of words in the text
            sentences (list): List of sentences in the text

        Returns:
            dict: Readability scores
        """
        if not words or not sentences:
            return {"flesch_reading_ease": 0, "flesch_kincaid_grade": 0}

        # Count syllables (simplified)
        syllable_count = 0
        for word in words:
            syllable_count += self._count_syllables(word)

        # Calculate scores
        words_per_sentence = len(words) / len(sentences)
        syllables_per_word = syllable_count / len(words)

        # Flesch Reading Ease
        flesch_reading_ease = (
            206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word)
        )
        flesch_reading_ease = max(0, min(100, flesch_reading_ease))

        # Flesch-Kincaid Grade Level
        flesch_kincaid_grade = (
            (0.39 * words_per_sentence) + (11.8 * syllables_per_word) - 15.59
        )
        flesch_kincaid_grade = max(0, flesch_kincaid_grade)

        return {
            "flesch_reading_ease": flesch_reading_ease,
            "flesch_kincaid_grade": flesch_kincaid_grade,
        }

    def _count_syllables(self, word):
        """
        Count syllables in a word (simplified method).

        Args:
            word (str): Word to count syllables for

        Returns:
            int: Number of syllables
        """
        # Simple syllable counting heuristic
        vowels = "aeiouy"
        word = word.lower()
        count = 0
        previous_is_vowel = False

        for char in word:
            if char in vowels:
                if not previous_is_vowel:
                    count += 1
                previous_is_vowel = True
            else:
                previous_is_vowel = False

        # Handle special cases
        if word.endswith("e"):
            count -= 1
        if count == 0:
            count = 1

        return count

    def _simple_sentiment_analysis(self, text):
        """
        Perform simple sentiment analysis on text.

        Args:
            text (str): Text to analyze

        Returns:
            dict: Sentiment scores
        """
        # Simple list of positive and negative words
        positive_words = {
            "good",
            "great",
            "excellent",
            "amazing",
            "awesome",
            "nice",
            "wonderful",
            "happy",
            "positive",
            "best",
            "love",
            "like",
            "enjoy",
            "beautiful",
            "perfect",
            "recommend",
            "recommended",
            "helpful",
            "impressed",
            "impressive",
            "easy",
            "excellent",
            "fantastic",
            "outstanding",
            "superb",
            "brilliant",
            "delight",
        }

        negative_words = {
            "bad",
            "terrible",
            "awful",
            "horrible",
            "poor",
            "worst",
            "hate",
            "dislike",
            "negative",
            "difficult",
            "hard",
            "boring",
            "disappointed",
            "disappointing",
            "waste",
            "useless",
            "problem",
            "issue",
            "defective",
            "broken",
            "unhappy",
            "fail",
            "failure",
            "failed",
            "terrible",
            "awful",
            "mediocre",
            "ugly",
        }

        # Count positive and negative words
        words = re.findall(r"\b\w+\b", text.lower())
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)

        # Calculate scores
        total_sentiment_words = positive_count + negative_count
        if total_sentiment_words == 0:
            return {"positive": 0, "negative": 0, "overall": 0}

        positive_score = positive_count / len(words) if words else 0
        negative_score = negative_count / len(words) if words else 0
        overall_score = (
            (positive_count - negative_count) / total_sentiment_words
            if total_sentiment_words > 0
            else 0
        )

        return {
            "positive": positive_score,
            "negative": negative_score,
            "overall": overall_score,
        }

    def _analyze_json_values(self, values):
        """
        Analyze a list of JSON values for statistics.

        Args:
            values (list): List of values to analyze

        Returns:
            dict: Value statistics
        """
        if not values:
            return {"type": "unknown", "count": 0}

        # Determine value type
        types = Counter(type(v).__name__ for v in values)
        most_common_type = types.most_common(1)[0][0]

        stats = {
            "type": most_common_type,
            "count": len(values),
            "unique_values": len({str(v) for v in values}),
        }

        # For numeric values, calculate statistics
        if most_common_type in ("int", "float"):
            numeric_values = [float(v) for v in values if isinstance(v, (int, float))]
            if numeric_values:
                stats.update(
                    {
                        "min": min(numeric_values),
                        "max": max(numeric_values),
                        "mean": sum(numeric_values) / len(numeric_values),
                        "median": sorted(numeric_values)[len(numeric_values) // 2],
                    }
                )

        # For strings, calculate length statistics
        elif most_common_type == "str":
            string_values = [v for v in values if isinstance(v, str)]
            if string_values:
                lengths = [len(s) for s in string_values]
                stats.update(
                    {
                        "min_length": min(lengths),
                        "max_length": max(lengths),
                        "avg_length": sum(lengths) / len(lengths),
                    }
                )

        return stats

    def _sanitize_math_expression(self, expr):
        """
        Sanitize a mathematical expression for safe evaluation.

        Args:
            expr (str): Expression to sanitize

        Returns:
            str: Sanitized expression
        """
        # Remove any characters that aren't digits, operators, or math functions
        allowed_pattern = r"[\d\s\+\-\*\/\(\)\.\,\^\%]|sqrt|abs|max|min|pow|round|sum|len|log|log10|sin|cos|tan|pi|e"
        sanitized = "".join(c for c in expr if re.match(allowed_pattern, c))

        # Replace ^ with ** for exponentiation
        sanitized = sanitized.replace("^", "**")

        return sanitized
