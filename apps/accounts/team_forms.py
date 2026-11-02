from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import User

from apps.activities.models import Activity

from .models import ActivityMembership, Role


class TeamMembershipForm(forms.Form):
    username = forms.CharField(
        label="Nom d'utilisateur",
        max_length=150,
        help_text="Pour un compte existant, ce nom ajoute uniquement un nouvel accès.",
    )
    first_name = forms.CharField(label="Prénom", max_length=150, required=False)
    last_name = forms.CharField(label="Nom", max_length=150, required=False)
    role = forms.ChoiceField(label="Rôle")
    is_active = forms.BooleanField(label="Accès actif", required=False, initial=True)
    user_is_active = forms.BooleanField(
        label="Compte autorisé à se connecter",
        required=False,
        initial=True,
    )
    password = forms.CharField(
        label="Mot de passe",
        required=False,
        widget=forms.PasswordInput,
        strip=False,
        help_text="Obligatoire à la création. Laissez vide pour ne pas le changer.",
    )

    def __init__(self, *args, activity=None, membership=None, global_admin=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.activity = activity
        self.membership = membership
        self.global_admin = global_admin
        self.existing_user = None
        self.shared_user = bool(
            membership
            and not global_admin
            and ActivityMembership.objects.filter(user=membership.user)
            .exclude(pk=membership.pk)
            .exists()
        )
        self.fields["role"].choices = (
            Role.choices if global_admin else [
                (Role.MANAGER, Role.MANAGER.label),
                (Role.EMPLOYEE, Role.EMPLOYEE.label),
            ]
        )
        if not membership:
            self.fields.pop("is_active")
            self.fields.pop("user_is_active")
        if not global_admin:
            if self.shared_user:
                for field_name in ("username", "first_name", "last_name"):
                    self.fields[field_name].disabled = True
                self.fields["username"].help_text = (
                    "Ce compte est aussi rattaché à une autre activité. "
                    "Seul le gérant global peut modifier ses informations communes."
                )
                self.fields.pop("password")
        if membership:
            user = membership.user
            self.initial.update(
                {
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": membership.role,
                    "is_active": membership.is_active,
                    "user_is_active": user.is_active,
                }
            )
        if global_admin:
            self.fields["activity"] = forms.ModelChoiceField(
                label="Activité",
                queryset=Activity.objects.all() if membership else Activity.objects.filter(is_active=True),
                required=False,
            )
            if membership:
                self.initial["activity"] = membership.activity_id
            self.order_fields(
                ["username", "first_name", "last_name", "password", "activity", "role"]
                + (["is_active", "user_is_active"] if membership else [])
            )
        elif membership:
            self.order_fields(
                ["username", "first_name", "last_name", "password", "role", "is_active"]
            )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        users = User.objects.filter(username__iexact=username)
        if self.membership:
            users = users.exclude(pk=self.membership.user_id)
        existing_user = users.first()
        if existing_user and not self.membership:
            self.existing_user = existing_user
        elif existing_user:
            raise forms.ValidationError("Ce nom d'utilisateur est déjà utilisé.")
        return username

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        activity = cleaned.get("activity") if self.global_admin else self.activity
        target_user = self.membership.user if self.membership else self.existing_user
        if role == Role.GLOBAL and self.global_admin and activity is not None:
            self.add_error("activity", "Un gérant global n'est lié à aucune activité.")
        elif role in (Role.MANAGER, Role.EMPLOYEE) and activity is None:
            if self.global_admin:
                self.add_error("activity", "Choisissez une activité pour ce rôle.")
            else:
                self.add_error(None, "Aucune activité n'est définie pour cette équipe.")

        password = cleaned.get("password")
        if not self.membership and not target_user and not password:
            self.add_error("password", "Le mot de passe est obligatoire pour un nouveau compte.")
        if password:
            try:
                password_validation.validate_password(
                    password,
                    self.membership.user if self.membership else None,
                )
            except forms.ValidationError as exc:
                self.add_error("password", exc)

        if target_user and role == Role.GLOBAL:
            other_active_memberships = ActivityMembership.objects.filter(
                user=target_user,
            ).exclude(pk=self.membership.pk)
            if other_active_memberships.exists():
                self.add_error(
                    "role",
                    "Retirez d'abord les autres rattachements de cette personne avant de lui attribuer le rôle global.",
                )
        if target_user and role in (Role.MANAGER, Role.EMPLOYEE) and activity:
            duplicate = ActivityMembership.objects.filter(
                user=target_user,
                activity=activity,
            )
            if self.membership:
                duplicate = duplicate.exclude(pk=self.membership.pk)
            if duplicate.exists():
                field = "activity" if self.global_admin else "role"
                self.add_error(
                    field,
                    "Cette personne possède déjà un accès à cette activité.",
                )
        if (
            target_user
            and role in (Role.MANAGER, Role.EMPLOYEE)
            and ActivityMembership.objects.filter(
                user=target_user,
                role=Role.GLOBAL,
                is_active=True,
            ).exists()
        ):
            self.add_error(
                "role",
                "Ce compte a déjà un accès global; aucun accès par activité n'est nécessaire.",
            )
        return cleaned

    def save(self):
        if not self.is_valid():
            raise ValueError("Le formulaire doit être valide avant l'enregistrement.")
        data = self.cleaned_data
        user = self.membership.user if self.membership else (self.existing_user or User())
        if not self.existing_user or self.membership:
            user.username = data["username"]
            user.first_name = data["first_name"]
            user.last_name = data["last_name"]
        password = data.get("password")
        if password:
            user.set_password(password)
        if self.global_admin and (self.membership or not self.existing_user):
            user.is_active = data.get("user_is_active", True)
        user.save()

        membership = self.membership or ActivityMembership(user=user)
        membership.user = user
        membership.role = data["role"]
        membership.activity = (
            data.get("activity") if self.global_admin else self.activity
        )
        membership.is_active = data.get("is_active", True)
        membership.save()
        return membership
