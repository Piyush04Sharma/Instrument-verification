from django.urls import path

from . import views

app_name = "verification"

urlpatterns = [
    # public
    path("verify/", views.verify_certificate, name="verify"),
    path("verify/<str:number>/", views.verify_certificate, name="verify_number"),
    # shopkeeper
    path("dashboard/", views.owner_dashboard, name="owner_dashboard"),
    path("applications/", views.application_list, name="application_list"),
    path("applications/new/", views.apply, name="apply"),
    path("applications/<int:pk>/", views.application_detail, name="application_detail"),
    path("applications/<int:pk>/pay/", views.pay, name="pay"),
    path("applications/<int:pk>/resubmit/", views.resubmit, name="resubmit"),
    path("applications/<int:pk>/documents/add/", views.add_document, name="add_document"),
    path("documents/<int:pk>/", views.document_download, name="document_download"),
    path("certificates/<str:number>/pdf/", views.certificate_pdf, name="certificate_pdf"),
    # notifications
    path("notifications/", views.notification_list, name="notifications"),
    path("notifications/read/", views.notifications_mark_read, name="notifications_read"),
    # officer
    path("officer/", views.officer_dashboard, name="officer_dashboard"),
    path("officer/applications/", views.officer_applications, name="officer_applications"),
    path("officer/applications/<int:pk>/", views.officer_application_detail, name="officer_application_detail"),
    path("officer/applications/<int:pk>/review/", views.officer_start_review, name="officer_start_review"),
    path("officer/applications/<int:pk>/schedule/", views.officer_schedule, name="officer_schedule"),
    path("officer/applications/<int:pk>/inspect/", views.officer_inspect, name="officer_inspect"),
    path("officer/applications/<int:pk>/approve/", views.officer_approve, name="officer_approve"),
    path("officer/applications/<int:pk>/reject/", views.officer_reject, name="officer_reject"),
    # administrator
    path("control/", views.admin_dashboard, name="admin_dashboard"),
    path("control/reports/", views.reports, name="reports"),
]
