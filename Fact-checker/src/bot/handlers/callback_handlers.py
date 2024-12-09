[... حفظ کد قبلی ...]

                    details.append(
                        f"• {claim['claim_text']}\n"
                        f"  نتیجه: {self._get_status_text(claim['verification_status'])}"
                    )

            if result.get('timeline'):
                details.append("\n⏱ خط زمانی رویداد:")
                for event in result['timeline']:
                    details.append(f"• {event['date']}: {event['description']}")

            return "\n".join(details)

        except Exception as e:
            logger.error(f"Error formatting detailed result: {str(e)}")
            return "متأسفانه در نمایش جزئیات مشکلی پیش آمد."

    async def _share_result(self, query, fact_check_id: int):
        """اشتراک‌گذاری نتیجه راستی‌آزمایی."""
        try:
            result = await self.fact_repository.get_fact_check(fact_check_id)
            if not result:
                await query.answer("اطلاعات این نتیجه در دسترس نیست.")
                return

            share_text = (
                f"🔍 نتیجه راستی‌آزمایی\n\n"
                f"ادعا: {result['claim_text']}\n\n"
                f"✅ نتیجه: {self._get_status_text(result['verification_status'])}\n"
                f"📊 درصد اطمینان: {result['credibility_score']*100:.1f}%\n\n"
                f"📝 خلاصه تحلیل:\n{result.get('summary', '')}\n\n"
                f"🤖 بررسی شده توسط ربات فکت‌چکر @factchecker_bot"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "📤 اشتراک در تلگرام",
                        url=f"https://t.me/share/url?url={quote(share_text)}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "↩️ بازگشت",
                        callback_data=f'{{"action":"show_details","id":{fact_check_id}}}'
                    )
                ]
            ]

            await query.message.edit_text(
                "برای اشتراک‌گذاری نتیجه از دکمه زیر استفاده کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Error sharing result: {str(e)}")
            await query.answer("متأسفانه در اشتراک‌گذاری مشکلی پیش آمد.")

    async def _handle_feedback(self, query, fact_check_id: int, value: str):
        """مدیریت بازخورد کاربر."""
        try:
            feedback_options = {
                'agree': ('موافق', '👍'),
                'disagree': ('مخالف', '👎')
            }

            if value in feedback_options:
                status, emoji = feedback_options[value]
                
                # ذخیره بازخورد در دیتابیس
                await self.fact_repository.save_feedback(
                    user_id=query.from_user.id,
                    fact_check_id=fact_check_id,
                    feedback_type=value
                )

                await query.message.edit_text(
                    f"{emoji} نظر شما ثبت شد.\n\n"
                    f"شما با نتیجه این راستی‌آزمایی {status} هستید.\n"
                    "آیا مایلید توضیحات بیشتری اضافه کنید؟",
                    reply_markup=inline_keyboards.get_feedback_detail_keyboard(fact_check_id)
                )

        except Exception as e:
            logger.error(f"Error handling feedback: {str(e)}")
            await query.answer("متأسفانه در ثبت نظر مشکلی پیش آمد.")

    async def _prepare_comment_input(self, query, fact_check_id: int):
        """آماده‌سازی دریافت نظر کاربر."""
        try:
            context = query._context
            context.user_data['expecting_comment'] = fact_check_id

            await query.message.edit_text(
                "✍️ لطفاً نظر خود را درباره این نتیجه بنویسید:\n\n"
                "• نظر شما باید مرتبط با موضوع باشد\n"
                "• حداقل ۱۰ و حداکثر ۵۰۰ کاراکتر مجاز است\n"
                "• از ارسال محتوای نامناسب خودداری کنید",
                reply_markup=inline_keyboards.get_confirmation_keyboard('cancel_comment')
            )

        except Exception as e:
            logger.error(f"Error preparing comment input: {str(e)}")
            await query.answer("متأسفانه در شروع فرآیند ثبت نظر مشکلی پیش آمد.")

    async def _prepare_issue_report(self, query, fact_check_id: int):
        """آماده‌سازی دریافت گزارش مشکل."""
        try:
            context = query._context
            context.user_data['expecting_report'] = fact_check_id

            keyboard = [
                [
                    InlineKeyboardButton(
                        "❌ اطلاعات نادرست",
                        callback_data=f'{{"action":"report_type","id":{fact_check_id},"type":"incorrect"}}'
                    ),
                    InlineKeyboardButton(
                        "🔗 منابع نامعتبر",
                        callback_data=f'{{"action":"report_type","id":{fact_check_id},"type":"sources"}}'
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⚠️ محتوای نامناسب",
                        callback_data=f'{{"action":"report_type","id":{fact_check_id},"type":"inappropriate"}}'
                    ),
                    InlineKeyboardButton(
                        "🔄 خطای سیستمی",
                        callback_data=f'{{"action":"report_type","id":{fact_check_id},"type":"system"}}'
                    )
                ],
                [
                    InlineKeyboardButton(
                        "↩️ بازگشت",
                        callback_data=f'{{"action":"show_details","id":{fact_check_id}}}'
                    )
                ]
            ]

            await query.message.edit_text(
                "⚠️ گزارش مشکل\n\n"
                "لطفاً نوع مشکل را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Error preparing issue report: {str(e)}")
            await query.answer("متأسفانه در شروع فرآیند گزارش مشکل خطایی رخ داد.")

    async def _update_result(self, query, analysis_result: Dict, fact_check_id: int):
        """به‌روزرسانی نتیجه راستی‌آزمایی."""
        try:
            # ذخیره نتیجه جدید در دیتابیس
            await self.fact_repository.update_result(
                fact_check_id=fact_check_id,
                new_result=analysis_result
            )

            # به‌روزرسانی پیام
            details = await self._format_detailed_result(analysis_result)
            await query.message.edit_text(
                f"🔄 نتیجه به‌روزرسانی شد\n\n{details}",
                reply_markup=inline_keyboards.get_verification_result_keyboard(analysis_result)
            )

        except Exception as e:
            logger.error(f"Error updating result: {str(e)}")
            await query.answer("متأسفانه در به‌روزرسانی نتیجه مشکلی پیش آمد.")

    def _get_status_text(self, status: str) -> str:
        """تبدیل وضعیت به متن فارسی."""
        status_texts = {
            'VERIFIED': 'تأیید شده',
            'FALSE': 'نادرست',
            'PARTIALLY_TRUE': 'نسبتاً درست',
            'UNVERIFIED': 'غیرقابل تأیید',
            'MISLEADING': 'گمراه‌کننده'
        }
        return status_texts.get(status, 'نامشخص')


def register_callback_handlers(application):
    """ثبت تمام هندلرهای کال‌بک."""
    handlers = CallbackHandlers()
    
    # هندلر کال‌بک‌های منوی اصلی
    application.add_handler(CallbackQueryHandler(
        handlers.handle_menu_callback,
        pattern=r'^{"action":"[^"]+"}$'
    ))
    
    # هندلر کال‌بک‌های نتایج
    application.add_handler(CallbackQueryHandler(
        handlers.handle_result_callback,
        pattern=r'^{"action":"[^"]+","id":\d+.*}$'
    ))
    
    # هندلر کال‌بک‌های تنظیمات
    application.add_handler(CallbackQueryHandler(
        handlers.handle_settings_callback,
        pattern=r'^{"setting":"[^"]+".*}$'
    ))