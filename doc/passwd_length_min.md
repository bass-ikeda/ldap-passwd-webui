# password_length_min

To limit the shortest length of a new password,
set `password_length_min` at `[html]` section, in `settings.ini`, like:

```
[html]
passwd_length_min = 10
```

Default: 8


## confirmation

By this setting, would change the top page.
see HTML source:

```
<label for="new-password">New password</label>
<input id="new-password" name="new-password" type="password"
    pattern=".{8,}" 
             ^^^^^
    oninvalid="setCustomValidity('Password must be at least 8 characters long.')" 
                                                           ^^^
    oninput="setCustomValidity('')"
    required>
```

... and also affects password validation in `app.py`:

```
if len(form('new-password')) < int(passwd_length_min):
    return error(_("Password must be at least ")    \
                 + str(passwd_length_min)           \
                 + _(" characters long!")
    )
```
