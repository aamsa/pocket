from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard(request):
    return render(request, "dashboard.html", {})


def health(request):
    from django.http import JsonResponse
    return JsonResponse({"status": "ok"})
