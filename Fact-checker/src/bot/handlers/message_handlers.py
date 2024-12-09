[... حفظ کد قبلی ...]

                    f"• متن تشخیص داده شده: {len(ocr['text'])} کاراکتر\n"
                    f"• زبان: {ocr.get('language', 'نامشخص')}\n"
                    f"• اطمینان تشخیص: {ocr.get('confidence', 0) * 100:.1f}%"
                )

            elif media_type == "video" and media_analysis.get('video_analysis'):
                analysis = media_analysis['video_analysis']
                info = [
                    "• تحلیل فریم‌های کلیدی:",
                ]
                
                if analysis.get('key_frames'):
                    for frame in analysis['key_frames'][:3]:  # نمایش 3 فریم مهم
                        info.append(f"  - {frame.get('description', '')}")
                        
                if analysis.get('transcription'):
                    info.append(f"\n• متن استخراج شده از صدا:")
                    info.append(f"  {analysis['transcription'][:200]}...")  # نمایش 200 کاراکتر اول
                    
                if analysis.get('detected_objects'):
                    objects = analysis['detected_objects'][:5]  # 5 شیء مهم
                    info.append(f"\n• اشیاء شناسایی شده:")
                    for obj in objects:
                        info.append(f"  - {obj['name']} ({obj['confidence']*100:.1f}%)")
                
                return "\n".join(info)

            elif media_type == "voice" and media_analysis.get('transcription'):
                trans = media_analysis['transcription']
                return (
                    f"• متن تشخیص داده شده:\n"
                    f"  {trans['text']}\n"
                    f"• زبان: {trans.get('language', 'نامشخص')}\n"
                    f"• اطمینان تشخیص: {trans.get('confidence', 0) * 100:.1f}%"
                )

            elif media_type == "document":
                doc_info = []
                
                if media_analysis.get('page_count'):
                    doc_info.append(f"• تعداد صفحات: {media_analysis['page_count']}")
                    
                if media_analysis.get('word_count'):
                    doc_info.append(f"• تعداد کلمات: {media_analysis['word_count']}")
                    
                if media_analysis.get('file_name'):
                    doc_info.append(f"• نام فایل: {media_analysis['file_name']}")
                    
                return "\n".join(doc_info) if doc_info else None

            return None

        except Exception as e:
            logger.error(f"Error getting media specific info: {str(e)}")
            return None

def register_message_handlers(application):
    """ثبت تمام هندلرهای پیام."""
    handlers = MessageHandlers()
    
    # هندلر پیام‌های متنی
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handlers.handle_text
    ))
    
    # هندلر تصاویر
    application.add_handler(MessageHandler(
        filters.PHOTO,
        handlers.handle_image
    ))
    
    # هندلر ویدیوها
    application.add_handler(MessageHandler(
        filters.VIDEO,
        handlers.handle_video
    ))
    
    # هندلر پیام‌های صوتی
    application.add_handler(MessageHandler(
        filters.VOICE,
        handlers.handle_voice
    ))
    
    # هندلر اسناد
    application.add_handler(MessageHandler(
        filters.Document.ALL,
        handlers.handle_document
    ))