[... کد قبلی حفظ می‌شود ...]

                # امتیاز نهایی جمله
                sentence_scores[sentence] = (
                    position_score + length_score + keyword_score
                ) / 3
            
            # انتخاب جملات برای خلاصه
            sorted_sentences = sorted(
                sentence_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            summary_sentences = []
            current_length = 0
            
            for sentence, _ in sorted_sentences:
                if current_length + len(sentence) <= max_length:
                    summary_sentences.append(sentence)
                    current_length += len(sentence)
                else:
                    break
            
            # مرتب‌سازی جملات بر اساس ترتیب اصلی
            summary_sentences.sort(
                key=lambda x: sentences.index(x)
            )
            
            summary = ' '.join(summary_sentences)
            compression_ratio = len(summary) / len(text)
            
            return {
                'summary': summary,
                'compression_ratio': compression_ratio,
                'selected_sentences': len(summary_sentences),
                'total_sentences': len(sentences)
            }
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return {
                'summary': '',
                'compression_ratio': 0.0,
                'error': str(e)
            }

    async def analyze_topics(self, text: str) -> Dict[str, List[Dict]]:
        """
        تحلیل موضوعی متن
        
        Args:
            text: متن ورودی
            
        Returns:
            موضوعات اصلی و فرعی با درصد اطمینان
        """
        try:
            # استخراج موضوعات اصلی با مدل طبقه‌بندی
            main_topics = await self._classify_topics(text)
            
            # استخراج موضوعات فرعی با تحلیل معنایی
            subtopics = await self._extract_subtopics(text, main_topics)
            
            # تحلیل ارتباطات موضوعی
            topic_relations = self._analyze_topic_relations(main_topics, subtopics)
            
            return {
                'main_topics': main_topics,
                'subtopics': subtopics,
                'topic_relations': topic_relations
            }
            
        except Exception as e:
            logger.error(f"Error analyzing topics: {str(e)}")
            return {
                'main_topics': [],
                'subtopics': [],
                'topic_relations': []
            }

    async def _classify_topics(self, text: str) -> List[Dict]:
        """
        طبقه‌بندی موضوعات اصلی متن
        """
        try:
            # لیست موضوعات از پیش تعریف شده
            predefined_topics = [
                "سیاسی", "اقتصادی", "اجتماعی", "فرهنگی",
                "علمی", "ورزشی", "هنری", "پزشکی"
            ]
            
            # تبدیل متن به بردار با استفاده از مدل BERT
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512
            )
            
            # پیش‌بینی موضوع
            outputs = self.classification_model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=1)
            
            topics = []
            for topic, score in zip(predefined_topics, predictions[0]):
                if score > 0.1:  # فقط موضوعات با اطمینان بالای 10٪
                    topics.append({
                        'topic': topic,
                        'confidence': float(score)
                    })
            
            return sorted(topics, key=lambda x: x['confidence'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error classifying topics: {str(e)}")
            return []

    async def _extract_subtopics(
        self,
        text: str,
        main_topics: List[Dict]
    ) -> List[Dict]:
        """
        استخراج موضوعات فرعی با تحلیل معنایی
        """
        try:
            subtopics = []
            doc = self.nlp(text)
            
            # استخراج عبارات اسمی
            noun_phrases = [chunk.text for chunk in doc.noun_chunks]
            
            # گروه‌بندی عبارات مشابه
            from sklearn.cluster import DBSCAN
            
            # تبدیل عبارات به بردار با Word2Vec
            phrase_vectors = []
            for phrase in noun_phrases:
                words = phrase.split()
                if not words:
                    continue
                vectors = []
                for word in words:
                    try:
                        vector = self.word2vec_model.wv[word]
                        vectors.append(vector)
                    except KeyError:
                        continue
                if vectors:
                    phrase_vectors.append(np.mean(vectors, axis=0))
            
            if not phrase_vectors:
                return []
            
            # خوشه‌بندی عبارات
            clustering = DBSCAN(eps=0.5, min_samples=2).fit(phrase_vectors)
            
            # استخراج موضوعات فرعی از هر خوشه
            for label in set(clustering.labels_):
                if label == -1:  # نویز
                    continue
                    
                cluster_phrases = [
                    noun_phrases[i] for i in range(len(noun_phrases))
                    if clustering.labels_[i] == label
                ]
                
                # انتخاب نماینده خوشه
                representative = max(
                    cluster_phrases,
                    key=lambda x: len(x.split())
                )
                
                subtopics.append({
                    'phrase': representative,
                    'frequency': len(cluster_phrases),
                    'variations': cluster_phrases,
                    'parent_topic': self._find_parent_topic(
                        representative,
                        main_topics
                    )
                })
            
            return subtopics
            
        except Exception as e:
            logger.error(f"Error extracting subtopics: {str(e)}")
            return []

    def _find_parent_topic(
        self,
        phrase: str,
        main_topics: List[Dict]
    ) -> Optional[str]:
        """
        یافتن موضوع اصلی مرتبط با عبارت
        """
        try:
            # محاسبه شباهت معنایی با موضوعات اصلی
            max_similarity = 0
            parent_topic = None
            
            phrase_vector = np.mean([
                self.word2vec_model.wv[word]
                for word in phrase.split()
                if word in self.word2vec_model.wv
            ], axis=0)
            
            for topic in main_topics:
                topic_vector = np.mean([
                    self.word2vec_model.wv[word]
                    for word in topic['topic'].split()
                    if word in self.word2vec_model.wv
                ], axis=0)
                
                similarity = cosine_similarity(
                    [phrase_vector],
                    [topic_vector]
                )[0][0]
                
                if similarity > max_similarity:
                    max_similarity = similarity
                    parent_topic = topic['topic']
            
            return parent_topic if max_similarity > 0.3 else None
            
        except Exception as e:
            logger.error(f"Error finding parent topic: {str(e)}")
            return None

    def _analyze_topic_relations(
        self,
        main_topics: List[Dict],
        subtopics: List[Dict]
    ) -> List[Dict]:
        """
        تحلیل ارتباطات بین موضوعات
        """
        try:
            relations = []
            
            for topic1 in main_topics:
                for topic2 in main_topics:
                    if topic1['topic'] >= topic2['topic']:
                        continue
                        
                    # یافتن موضوعات فرعی مشترک
                    common_subtopics = [
                        sub for sub in subtopics
                        if sub['parent_topic'] in [topic1['topic'], topic2['topic']]
                    ]
                    
                    if common_subtopics:
                        relations.append({
                            'topic1': topic1['topic'],
                            'topic2': topic2['topic'],
                            'strength': len(common_subtopics) / len(subtopics),
                            'common_subtopics': [
                                sub['phrase'] for sub in common_subtopics
                            ]
                        })
            
            return relations
            
        except Exception as e:
            logger.error(f"Error analyzing topic relations: {str(e)}")
            return []

    async def extract_patterns(self, text: str) -> Dict[str, List[Dict]]:
        """
        استخراج الگوهای مختلف از متن
        
        Args:
            text: متن ورودی
            
        Returns:
            دیکشنری انواع الگوهای یافت شده
        """
        try:
            results = {}
            
            # استخراج الگوها برای هر نوع
            for pattern_type, patterns in self.patterns.items():
                matches = []
                for pattern in patterns:
                    for match in re.finditer(pattern, text):
                        matches.append({
                            'text': match.group(),
                            'start': match.start(),
                            'end': match.end(),
                            'pattern': pattern
                        })
                
                results[pattern_type] = matches
            
            return results
            
        except Exception as e:
            logger.error(f"Error extracting patterns: {str(e)}")
            return {}

    def _calculate_text_statistics(self, text: str) -> Dict[str, any]:
        """
        محاسبه آمار متنی
        
        Args:
            text: متن ورودی
            
        Returns:
            دیکشنری آمار محاسبه شده
        """
        try:
            doc = self.nlp(text)
            
            # آمار پایه
            stats = {
                'char_count': len(text),
                'word_count': len([token for token in doc if not token.is_punct]),
                'sentence_count': len(list(doc.sents)),
                'paragraph_count': len(text.split('\n\n')),
                'average_word_length': np.mean([
                    len(token.text) for token in doc if not token.is_punct
                ]),
                'average_sentence_length': np.mean([
                    len([t for t in sent if not t.is_punct])
                    for sent in doc.sents
                ])
            }
            
            # آمار اجزای سخن
            pos_stats = Counter([token.pos_ for token in doc])
            stats['pos_distribution'] = dict(pos_stats)
            
            # آمار پیچیدگی متن
            stats['lexical_diversity'] = len(set(
                token.text.lower() for token in doc
                if not token.is_punct and not token.is_stop
            )) / stats['word_count']
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating text statistics: {str(e)}")
            return {}

    async def find_similar_texts(
        self,
        text: str,
        candidates: List[str],
        threshold: float = 0.7
    ) -> List[Dict[str, any]]:
        """
        یافتن متون مشابه
        
        Args:
            text: متن مورد نظر
            candidates: لیست متون کاندید
            threshold: آستانه شباهت
            
        Returns:
            لیست متون مشابه با امتیاز شباهت
        """
        try:
            # تبدیل متون به بردار
            vectorizer = TfidfVectorizer()
            vectors = vectorizer.fit_transform([text] + candidates)
            
            # محاسبه شباهت
            similarities = cosine_similarity(vectors[0:1], vectors[1:])
            
            similar_texts = []
            for i, score in enumerate(similarities[0]):
                if score >= threshold:
                    similar_texts.append({
                        'text': candidates[i],
                        'similarity_score': float(score)
                    })
            
            return sorted(
                similar_texts,
                key=lambda x: x['similarity_score'],
                reverse=True
            )
            
        except Exception as e:
            logger.error(f"Error finding similar texts: {str(e)}")
            return []

    async def close(self):
        """
        آزادسازی منابع
        """
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)

    def __del__(self):
        """
        پاکسازی منابع هنگام حذف شیء
        """
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
