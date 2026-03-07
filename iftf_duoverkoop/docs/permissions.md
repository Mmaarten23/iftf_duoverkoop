# Permissions Reference

This document describes every permission used in the application, which groups
hold them, and how they are enforced at each layer.  
Run `python manage.py setup_permissions` after any change to groups/permissions
to apply them to the live database.

---

## Groups

| Group | Intended for |
|---|---|
| **POS Staff** | Ticket desk operators who sell tickets on the day |
| **Support Staff** | Back-office staff who manage purchases, export data and verify tickets |
| **Association Representative** | Representatives from the participating associations who only need to verify a ticket code at the door |

---

## Permissions

All permissions live on the `Purchase` model (`iftf_duoverkoop.Purchase`).

| Codename | Label | Django built-in? |
|---|---|---|
| `add_purchase` | Can add purchase | ✅ auto-generated |
| `view_purchase` | Can view purchase | ✅ auto-generated |
| `change_purchase` | Can change purchase | ✅ auto-generated |
| `delete_purchase` | Can delete purchase | ✅ auto-generated |
| `export_data` | Can export purchase data to CSV | ❌ custom (`Purchase.Meta.permissions`) |
| `verify_purchase` | Can look up purchases by verification code | ❌ custom (`Purchase.Meta.permissions`) |

---

## Group → Permission Matrix

| Permission | POS Staff | Support Staff | Association Rep |
|---|---|---|---|
| `add_purchase` | ✅ | ✅ | ❌ |
| `view_purchase` | ✅ | ✅ | ❌ |
| `change_purchase` | ❌ | ✅ | ❌ |
| `delete_purchase` | ❌ | ✅ | ❌ |
| `export_data` | ❌ | ✅ | ❌ |
| `verify_purchase` | ❌ | ✅ | ✅ |

---

## View-Level Enforcement

| View / URL | Decorator(s) | Required permission |
|---|---|---|
| `order` — sell a ticket | `@login_required` | Any authenticated user |
| `purchase_history` — read-only list | `@login_required` + `@permission_required` | `view_purchase` |
| `edit_purchase` — AJAX edit | `@login_required` + `@permission_required` | `change_purchase` |
| `delete_purchase` — AJAX delete | `@login_required` + `@permission_required` | `delete_purchase` |
| `verify_code` — lookup by code | `@login_required` + `@permission_required` | `verify_purchase` |
| `export` — CSV download | `@login_required` + `@permission_required` | `export_data` |
| `get_performance_prices` | `@login_required` | Any authenticated user |
| `get_performances_by_association` | `@login_required` | Any authenticated user |
| `db_info` | `@login_required` | Any authenticated user |
| `get_last_customer` | `@login_required` | Any authenticated user |
| `login_view` / `logout_view` | — / `@login_required` | Public / any authenticated user |

---

## Template-Level Enforcement

| Template | Variable / tag | Controls |
|---|---|---|
| `purchase_history.html` | `{% if user_can_edit %}` | Edit & Delete **buttons** in the purchase list |
| `purchase_history.html` | `{% if user_can_edit %}` | Edit **modal HTML** and edit/delete **JavaScript** |
| `base.html` (navbar) | `{% if perms.iftf_duoverkoop.verify_purchase %}` | Verify link in navigation |
| `base.html` (navbar) | `{% if perms.iftf_duoverkoop.export_data %}` | Export link in navigation |
| `base.html` (navbar) | `{% if user.is_superuser %}` | Admin link in navigation |

`user_can_edit` is computed in the `purchase_history` view as:

```python
user_can_edit = user.has_perm('iftf_duoverkoop.change_purchase')
```

---

## Helper Functions (`auth.py`)

| Function | Returns `True` when… |
|---|---|
| `is_pos_staff(user)` | User is a member of the POS Staff group |
| `is_support_staff(user)` | User is a member of the Support Staff group |
| `is_association_rep(user)` | User is a member of the Association Representative group |
| `can_edit_purchases(user)` | User has `change_purchase` permission |
| `can_export_data(user)` | User has `export_data` permission |
| `can_verify_tickets(user)` | User has `verify_purchase` permission |

---

## Management Commands

```
# Create / re-sync all three groups and their permissions
python manage.py setup_permissions

# Assign a user to a group (removes them from any other group first)
python manage.py assign_user_group <username> "POS Staff"
python manage.py assign_user_group <username> "Support Staff"
python manage.py assign_user_group <username> "Association Representative"
```

---

## Adding a New Permission

1. Add the codename + label to `Purchase.Meta.permissions` in `models.py`.
2. Create a migration (`python manage.py makemigrations`).
3. Add it to the relevant group(s) in `auth.py → setup_permission_groups()`.
4. Run `python manage.py setup_permissions` on the server.
5. Protect the view with `@permission_required('iftf_duoverkoop.<codename>', raise_exception=True)`.
6. Update this document.

