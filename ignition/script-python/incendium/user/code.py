"""User module."""

from __future__ import unicode_literals

__all__ = [
    "IncendiumUser",
    "get_emails",
    "get_user",
    "get_user_email_address",
    "get_user_first_name",
    "get_user_full_name",
    "get_users",
]

import system.security
import system.user
from com.inductiveautomation.ignition.common.user import ContactInfo, PyUser

from incendium.exceptions import ApplicationError


class IncendiumUser(object):
    """Wrapper class for Ignition's User object."""

    def __init__(self, user):
        """User initializer.

        Args:
            user (PyUser): Ignition's user object.
        """
        super(IncendiumUser, self).__init__()
        self._contact_info = user.getContactInfo()
        self._email = None
        self._first_name = user.get(user.FirstName)
        self._last_name = user.get(user.LastName)
        self._locale = user.getOrDefault(user.Language)
        self._roles = user.getRoles()

    @property
    def contact_info(self):
        """Get User's ContactInfo.

        Returns:
            list[ContactInfo]: A sequence of ContactInfo objects.
        """
        return self._contact_info

    @property
    def email(self):
        """Get User's email address(es).

        Returns:
            list[str]: User's email address(es).
        """
        return [ci.value for ci in self._contact_info if ci.contactType == "email"]

    @property
    def first_name(self):
        """Get User's first name.

        Returns:
            str: User's first name.
        """
        return self._first_name

    @property
    def full_name(self):
        """Get User's full name.

        Returns:
            str: User's full name.
        """
        return " ".join([self._first_name, self._last_name])

    @property
    def last_name(self):
        """Get User's last name.

        Returns:
            str: User's last name.
        """
        return self._last_name

    @property
    def locale(self):
        """Get User's preferred language.

        Returns:
            str: User's preferred language.
        """
        return self._locale

    @property
    def roles(self):
        """Get User's Roles.

        Returns:
            list[str]: A list of Roles for this User.
        """
        return self._roles


def get_emails(user_source="", filter_role=""):
    """Get a list of email addresses from a User Source.

    Args:
        user_source (str): The name of the User Source. If not provided,
            the default User Source will be consulted. Optional.
        filter_role (str): The name of the role. If provided, a list of
            email addresses for users that are assigned to a matching
            role will be retrieved, otherwise all email addresses will
            be retrieved. Optional.

    Returns:
        list[str]: A list of email addresses.
    """
    emails = set()
    users = [IncendiumUser(user) for user in get_users(user_source, filter_role)]
    for user in users:
        for email in user.email:
            emails.add(email)
    return sorted(list(emails))


def get_user(user_source="", failover=None):
    """Look up the logged-in User in a User Source.

    Args:
        user_source (str): The name of the User Source. If not provided,
            the default User Source will be consulted. Optional.
        failover (str): The name of the Failover Source. Optional.

    Returns:
        IncendiumUser: An IncendiumUser object.

    Raises:
        ApplicationError: If User is not found.
    """
    username = system.security.getUsername()

    user = system.user.getUser(user_source, username)

    if user is None and failover:
        user = system.user.getUser(failover, username)

    if user is None:
        raise ApplicationError("User was not found.")

    return IncendiumUser(user)


def get_user_email_address(user_source="", failover=None):
    """Get the User's Email address(es).

    Args:
        user_source (str): The name of the User Source. If not provided,
            the default User Source will be consulted. Optional.
        failover (str): The name of the Fallback profile. Optional.

    Returns:
        list[str]: The User's Email address(es).
    """
    return get_user(user_source, failover).email


def get_user_first_name(user_source="", failover=None):
    """Get the User's First Name.

    Args:
        user_source (str): The name of the User Source. If not provided,
            the default User Source will be consulted. Optional.
        failover (str): The name of the Fallback profile. Optional.

    Returns:
        str: The User's First Name.
    """
    return get_user(user_source, failover).first_name


def get_user_full_name(user_source="", failover=None):
    """Get the User's Full Name.

    Args:
        user_source (str): The name of the User Source. If not provided,
            the default User Source will be consulted. Optional.
        failover (str): The name of the Fallback profile. Optional.

    Returns:
        str: The User's Full Name.
    """
    return get_user(user_source, failover).full_name


def get_users(user_source="", filter_role=""):
    """Get a list of PyUser objects from a User Source filtered by role.

    Args:
        user_source (str): The name of the User Source. If not provided,
            the default User Source will be consulted. Optional.
        filter_role (str): The name of the role. If provided, a list of
            PyUser objects for users that are assigned to a matching
            role will be retrieved, otherwise all users will be
            retrieved as PyUser objects. Optional.

    Returns:
        list[PyUser]: A list of PyUser objects.
    """
    users = system.user.getUsers(user_source)
    return (
        [user for user in users if filter_role in user.getRoles()]
        if filter_role
        else users
    )
