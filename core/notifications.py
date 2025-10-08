import logging
from typing import List
from django.db.models import Q
from .models import FloodAlert, EmergencyContact, NotificationLog, UserProfile

logger = logging.getLogger(__name__)


def dispatch_notifications_for_alert(alert: FloodAlert):
    """
    Finds relevant contacts for a given FloodAlert and creates NotificationLog entries.
    This simulates sending SMS and email notifications.

    Args:
        alert (FloodAlert): The alert for which to send notifications.
    """
    if not alert.active:
        logger.info(f"Alert {alert.id} is not active. Skipping notification dispatch.")
        return

    # Get all barangays affected by the alert
    affected_barangays = alert.affected_barangays.all()
    if not affected_barangays.exists():
        logger.warning(f"Alert {alert.id} has no affected barangays. No notifications sent.")
        return

    # --- Find Recipients ---
    # 1. EmergencyContact model entries for the affected barangays
    contacts = EmergencyContact.objects.filter(barangay__in=affected_barangays)

    # 2. UserProfile entries for users assigned to the affected locations
    # Find users assigned to the specific barangays or their parent municipalities
    barangay_ids = [b.id for b in affected_barangays]
    municipality_ids = [b.municipality_id for b in affected_barangays if b.municipality_id]

    users = UserProfile.objects.filter(
        Q(barangay_id__in=barangay_ids) | Q(municipality_id__in=municipality_ids)
    ).select_related('user')

    # --- Prepare and "Send" Notifications ---
    message_body = f"Flood Alert: {alert.get_severity_level_display()} - {alert.title}. Description: {alert.description}"
    recipients_notified = set()

    # Notify EmergencyContacts
    for contact in contacts:
        if contact.phone and contact.phone not in recipients_notified:
            # Simulate sending SMS
            NotificationLog.objects.create(
                alert=alert, notification_type='sms', recipient=contact.phone, status='sent'
            )
            recipients_notified.add(contact.phone)
            logger.info(f"Simulated SMS sent to emergency contact {contact.name} at {contact.phone} for alert {alert.id}")

    # Notify UserProfiles
    for profile in users:
        # Notify via Email
        if profile.receive_email and profile.user.email and profile.user.email not in recipients_notified:
            NotificationLog.objects.create(
                alert=alert, notification_type='email', recipient=profile.user.email, status='sent'
            )
            recipients_notified.add(profile.user.email)
            logger.info(f"Simulated Email sent to user {profile.user.username} at {profile.user.email} for alert {alert.id}")
        # Notify via SMS
        if profile.receive_sms and profile.phone_number and profile.phone_number not in recipients_notified:
            NotificationLog.objects.create(
                alert=alert, notification_type='sms', recipient=profile.phone_number, status='sent'
            )
            recipients_notified.add(profile.phone_number)
            logger.info(f"Simulated SMS sent to user {profile.user.username} at {profile.phone_number} for alert {alert.id}")

    logger.info(f"Dispatched notifications for alert {alert.id} to {len(recipients_notified)} unique recipients.")