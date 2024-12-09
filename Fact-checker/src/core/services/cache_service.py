[... کد قبلی حفظ می‌شود ...]

    def get_stats(self) -> Dict[str, any]:
        """
        دریافت آمار عملکرد کش
        
        Returns:
            دیکشنری حاوی آمار
        """
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'total_requests': total_requests,
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': hit_rate,
            'memory_hits': self.stats['memory_hits'],
            'file_hits': self.stats['file_hits'],
            'redis_hits': self.stats['redis_hits'],
            'memory_cache_size': len(self.memory_cache),
            'file_cache_size': self._get_file_cache_size(),
            'redis_cache_size': self._get_redis_size(),
            'last_cleanup': self._get_last_cleanup_time()
        }

    def _get_file_cache_size(self) -> int:
        """
        محاسبه حجم کش فایل
        
        Returns:
            حجم به بایت
        """
        try:
            total_size = 0
            for file in os.listdir(self.cache_dir):
                if file.endswith('.cache'):
                    file_path = os.path.join(self.cache_dir, file)
                    total_size += os.path.getsize(file_path)
            return total_size
        except Exception as e:
            logger.error(f"Error calculating file cache size: {str(e)}")
            return 0

    async def _get_redis_size(self) -> int:
        """
        دریافت تعداد کلیدهای Redis
        
        Returns:
            تعداد کلیدها
        """
        try:
            if self.redis:
                return await self.redis.dbsize()
            return 0
        except Exception as e:
            logger.error(f"Error getting Redis size: {str(e)}")
            return 0

    async def get_keys(
        self,
        pattern: str = '*',
        namespace: Optional[str] = None
    ) -> List[str]:
        """
        دریافت لیست کلیدهای موجود در کش
        
        Args:
            pattern: الگوی جستجو
            namespace: فضای نام
            
        Returns:
            لیست کلیدها
        """
        try:
            if namespace:
                pattern = f"{namespace}:{pattern}"
                
            keys = set()
            
            # کلیدهای حافظه
            memory_keys = {
                k.split(':', 1)[1] if ':' in k else k
                for k in self.memory_cache.keys()
                if k.startswith(pattern.replace('*', ''))
            }
            keys.update(memory_keys)
            
            # کلیدهای Redis
            if self.redis:
                redis_keys = await self.redis.keys(pattern)
                redis_keys = {
                    k.decode().split(':', 1)[1] if ':' in k.decode() else k.decode()
                    for k in redis_keys
                }
                keys.update(redis_keys)
            
            # کلیدهای فایل
            import glob
            file_pattern = os.path.join(self.cache_dir, f"{pattern}.cache")
            file_keys = {
                os.path.splitext(os.path.basename(f))[0].split(':', 1)[1]
                if ':' in os.path.basename(f)
                else os.path.splitext(os.path.basename(f))[0]
                for f in glob.glob(file_pattern)
            }
            keys.update(file_keys)
            
            return sorted(list(keys))
            
        except Exception as e:
            logger.error(f"Error getting cache keys: {str(e)}")
            return []

    async def get_namespaces(self) -> List[str]:
        """
        دریافت لیست فضاهای نام موجود
        
        Returns:
            لیست فضاهای نام
        """
        try:
            namespaces = set()
            
            # فضاهای نام حافظه
            memory_namespaces = {
                k.split(':', 1)[0] for k in self.memory_cache.keys()
                if ':' in k
            }
            namespaces.update(memory_namespaces)
            
            # فضاهای نام Redis
            if self.redis:
                redis_keys = await self.redis.keys('*')
                redis_namespaces = {
                    k.decode().split(':', 1)[0] for k in redis_keys
                    if ':' in k.decode()
                }
                namespaces.update(redis_namespaces)
            
            # فضاهای نام فایل
            for file in os.listdir(self.cache_dir):
                if ':' in file and file.endswith('.cache'):
                    namespace = file.split(':', 1)[0]
                    namespaces.add(namespace)
            
            return sorted(list(namespaces))
            
        except Exception as e:
            logger.error(f"Error getting cache namespaces: {str(e)}")
            return []

    async def monitor(
        self,
        duration: int = 60,
        interval: int = 1
    ) -> List[Dict[str, any]]:
        """
        نظارت بر عملکرد کش
        
        Args:
            duration: مدت نظارت به ثانیه
            interval: فاصله نمونه‌برداری به ثانیه
            
        Returns:
            لیست آمار در بازه‌های زمانی
        """
        try:
            stats_history = []
            iterations = duration // interval
            
            for _ in range(iterations):
                stats = {
                    'timestamp': datetime.now().isoformat(),
                    'memory_usage': len(self.memory_cache),
                    'file_usage': self._get_file_cache_size(),
                    'hit_rate': await self._calculate_hit_rate(),
                    'operations_per_second': await self._calculate_ops_rate()
                }
                
                if self.redis:
                    stats['redis_usage'] = await self.redis.dbsize()
                    
                stats_history.append(stats)
                await asyncio.sleep(interval)
            
            return stats_history
            
        except Exception as e:
            logger.error(f"Error monitoring cache: {str(e)}")
            return []

    def cached(
        self,
        ttl: Optional[int] = None,
        namespace: str = 'default'
    ):
        """
        دکوراتور برای کش کردن نتایج توابع
        
        Args:
            ttl: زمان انقضا به ثانیه
            namespace: فضای نام
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # ساخت کلید بر اساس تابع و پارامترها
                key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                
                # بررسی کش
                result = await self.get(key, namespace=namespace)
                if result is not None:
                    return result
                
                # اجرای تابع
                result = await func(*args, **kwargs)
                
                # ذخیره در کش
                await self.set(
                    key,
                    result,
                    ttl=ttl,
                    namespace=namespace
                )
                
                return result
            return wrapper
        return decorator

    async def health_check(self) -> Dict[str, bool]:
        """
        بررسی سلامت سرویس کش
        
        Returns:
            وضعیت بخش‌های مختلف
        """
        try:
            status = {
                'memory': True,
                'file': await self._check_file_system(),
                'redis': await self._check_redis()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error checking cache health: {str(e)}")
            return {
                'memory': False,
                'file': False,
                'redis': False
            }

    async def _check_file_system(self) -> bool:
        """
        بررسی دسترسی به سیستم فایل
        
        Returns:
            True در صورت سالم بودن
        """
        try:
            test_file = os.path.join(self.cache_dir, 'test.cache')
            with open(test_file, 'wb') as f:
                pickle.dump('test', f)
            os.remove(test_file)
            return True
        except Exception:
            return False

    async def _check_redis(self) -> bool:
        """
        بررسی اتصال Redis
        
        Returns:
            True در صورت سالم بودن
        """
        try:
            if self.redis:
                await self.redis.ping()
                return True
            return False
        except Exception:
            return False

    async def backup(self, backup_dir: str):
        """
        تهیه نسخه پشتیبان از کش
        
        Args:
            backup_dir: مسیر ذخیره نسخه پشتیبان
        """
        try:
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # پشتیبان‌گیری از کش حافظه
            memory_backup_file = os.path.join(
                backup_dir,
                f'memory_cache_{timestamp}.pkl'
            )
            with open(memory_backup_file, 'wb') as f:
                pickle.dump(self.memory_cache, f)
            
            # پشتیبان‌گیری از کش فایل
            import shutil
            file_backup_dir = os.path.join(backup_dir, f'file_cache_{timestamp}')
            shutil.copytree(self.cache_dir, file_backup_dir)
            
            # پشتیبان‌گیری از Redis
            if self.redis:
                redis_backup_file = os.path.join(
                    backup_dir,
                    f'redis_cache_{timestamp}.rdb'
                )
                await self.redis.save()
                # کپی فایل RDB
                
            logger.info(f"Cache backup created at {backup_dir}")
            
        except Exception as e:
            logger.error(f"Error creating cache backup: {str(e)}")
            raise

    async def restore(self, backup_dir: str):
        """
        بازیابی نسخه پشتیبان کش
        
        Args:
            backup_dir: مسیر نسخه پشتیبان
        """
        try:
            # بازیابی کش حافظه
            memory_backup = sorted(
                f for f in os.listdir(backup_dir)
                if f.startswith('memory_cache_')
            )[-1]
            with open(os.path.join(backup_dir, memory_backup), 'rb') as f:
                self.memory_cache = pickle.load(f)
            
            # بازیابی کش فایل
            file_backup = sorted(
                f for f in os.listdir(backup_dir)
                if f.startswith('file_cache_')
            )[-1]
            shutil.rmtree(self.cache_dir)
            shutil.copytree(
                os.path.join(backup_dir, file_backup),
                self.cache_dir
            )
            
            # بازیابی Redis
            if self.redis:
                redis_backup = sorted(
                    f for f in os.listdir(backup_dir)
                    if f.startswith('redis_cache_')
                )[-1]
                # بازیابی فایل RDB
            
            logger.info(f"Cache restored from {backup_dir}")
            
        except Exception as e:
            logger.error(f"Error restoring cache backup: {str(e)}")
            raise

    async def close(self):
        """
        بستن اتصالات و آزادسازی منابع
        """
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()
            
        if self.executor:
            self.executor.shutdown(wait=True)

    def __del__(self):
        """
        پاکسازی منابع هنگام حذف شیء
        """
        if hasattr(self, 'redis') and self.redis:
            asyncio.run(self.redis.close())
