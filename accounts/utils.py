from .models import Profile


def get_profile(user):
    """Return the user's profile, creating it on first use.

    Superusers created with "createsuperuser" get the administrator role,
    everybody else starts as a shopkeeper.
    """
    if not user.is_authenticated:
        return None
    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={"role": Profile.ADMIN if user.is_superuser else Profile.OWNER},
    )
    return profile
