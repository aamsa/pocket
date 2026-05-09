def app_meta(request):
    ctx = {
        "APP_NAME": "Pocket",
        "APP_TAGLINE": "Mindful money for two",
        "GLOBAL_PENDING_INVITES": 0,
    }
    if request.user.is_authenticated:
        from apps.pockets.models import SHARE_STATUS_PENDING, PocketShare

        ctx["GLOBAL_PENDING_INVITES"] = PocketShare.objects.filter(
            shared_with=request.user, status=SHARE_STATUS_PENDING
        ).count()
    return ctx
