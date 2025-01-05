# hook support

By hook, You can add additional processes at:

+ password validation
+ changing password

set `program_password_*` at `[hook]` section, in `settings.ini`, like:

```
[hook]
program_password_policy = /path/to/program
program_password_change = /path/to/program
```


## program_password_policy

When you push `Update password` on Web UI, then `app.py` checks input data:

+ `New password` and `Confirm new password` are the same.
+ `New password` is longer than `passwd_length_min` (default: 8)

then, `app.py` calls the external program specified at 
`program_password_policy` setting.


## program_password_change

After password validations, `app.py` try to update LDAP passwords.

then, `app.py` calls the external program specified at 
`program_password_change` setting.


----
# Example

1. write a program for password validation, and save it.
2. set `program_password_* = /path/to/program` in `settings.ini`

## sample program: validator.pl

```
#!/usr/bin/perl

use strict;
use warnings;
use utf8;

# read 4 lines from STDIN
my ($username,       # STDIN line 1
    $old_pass,       # STDIN line 2
    $new_pass,       # STDIN line 3
    $confirm_pass    # STDIN line 4
) = <STDIN>;

foreach ( $username, $old_pass, $new_pass, $confirm_pass )
{
    $_ = '' if ( !defined($_) );
}
chomp( $username, $old_pass, $new_pass, $confirm_pass );

#
# write to STDERR if new_pass is contrary to the password policy.
#

# check 1: NUMBER
if ($new_pass !~ /[0-9]/)
{
    print( STDERR "New-password MUST contain NUMBER charcters\n" );
}

# check 2: Upper and Lower letters
if (! ($new_pass =~ /[a-z]/ && $new_pass =~ /[A-Z]/) )
{
    print( STDERR "New-password MUST contain both Upper and Lower alphabets\n" );
}

exit(0);
```

save this as `/usr/local/bin/validator.pl`, 
and add executable permissions:

```
chown root:httpd /usr/local/bin/validator.pl
chmod ug+rx /usr/local/bin/validator.pl
```


## sample program: smbpasswd.pl

```
    : (snip)

use constant {
    SUDO      => '/usr/bin/sudo --non-interactive',
    SMBPASSWD => '/usr/bin/smbpasswd -s -D 0',
};

# 1. open `smbpasswd` through a pipeline
my $cmd = sprintf( "%s %s %s", SUDO, SMBPASSWD, $username );
open( my $fh, "|-", $cmd ) or die "Unable to open pipeline: $!";

# for LOG output
print( STDOUT "change SAMBA password: $username\n" );
print( STDOUT "- exec: $cmd\n" );
print( STDOUT "- by-id: " . qx( id ) );

# 2. type New Password Twice
#   - `smbpasswd -s` requests this
print( $fh "$new_pass\n" );
print( $fh "$new_pass\n" );
close($fh);

# smbpasswd would write some errors into STDERR
# ->app.py will STOP updating password and show ERROR messages on Web UI

exit(0);
```

`smbpasswd` needs root privileges to change password of others.
so, set `sudoers` like this:

```
## Allow user `ldap-passwd-webui` to run smbpasswd as root
ldap-passwd-webui       ALL = NOPASSWD: /usr/bin/smbpasswd
```


## sample settings in settings.ini

```
[hook]
program_password_policy = /usr/local/bin/validator.pl
program_password_change = /usr/local/bin/smbpasswd.pl
```


----
# Spec of hook programs

`app.py` expects that hook programs will satisfy the following specifications:

+ read 4 lines from STDIN
+ write ERROR messages into STDERR, to prevent password update
+ (optional) write debug messages into STDOUT


## INPUT

`app.py` sends 4 lines of input data to hook programs:

````
USERNAME
OLD_PASSWORD
NEW_PASSWORD
CONFIRM_NEW_PASSWORD
````

Hook programs read 4 lines from STDIN, and do some processes as you like.


## OUTPUT

Then hook programs write some messages into their STDOUT.
And if some error occurs, hook programs write some ERROR messages into their 
STDERR.

`app.py` reads STDOUT of hook programs, then write them into LOG, messages 
for debug.

`app.py` also reads STDERR of hook programs, write them into LOG as WARNING 
messages, and STOP updating passwords.


## user and groups

Hook programs are executed with the same user-group privileges as `app.py`.
If you need another user-group permissions, try `sudo` in the hook program.
