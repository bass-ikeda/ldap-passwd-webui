<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex, nofollow">

    <title>{{ page_title }}</title>

    <link rel="stylesheet" href="{{ url('static', filename='style.css') }}">
  </head>

  <body>
    <main>
      <h1>LDAP パスワードの変更</h1>

      <form method="post">
        <label for="username">ユーザー名</label>
        <input id="username" name="username" value="{{ get('username', '') }}" type="text" required autofocus>

        <label for="old-password">現在のパスワード</label>
        <input id="old-password" name="old-password" type="password" required>

        <%
        passwd_length_min = get('passwd_length_min', '8')
        pattern = ".{%s,}" % passwd_length_min
        %>
        <label for="new-password">新しいパスワード</label>
        <input id="new-password" name="new-password" type="password"
            pattern="{{ pattern }}" 
            oninvalid="setCustomValidity('パスワードは {{ passwd_length_min }} 文字以上で指定してください')" 
            oninput="setCustomValidity('')"
            required>

        <label for="confirm-password">新しいパスワードを もう一度</label>
        <input id="confirm-password" name="confirm-password" type="password"
            pattern="{{ pattern }}" 
            oninvalid="setCustomValidity('パスワードは {{ passwd_length_min }} 文字以上で指定してください')" 
            oninput="setCustomValidity('')"
            required>

        <input id="lang" name="lang" type="hidden" value="{{ get('lang', '') }}">

        <button type="submit">パスワードを変更する</button>
      </form>

      <div class="alerts">
        %for type, text in get('alerts', []):
          <div class="alert {{ type }}">{{ text }}</div>
        %end
      </div>
    </main>
  </body>
</html>
