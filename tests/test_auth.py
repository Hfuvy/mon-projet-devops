def test_signup_page(client):
    response = client.get('/signup')
    assert response.status_code == 200

def test_login_page(client):
    response = client.get('/login')
    assert response.status_code == 200

def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200

def test_dashboard_requires_login(client):
    response = client.get('/dashboard', follow_redirects=False)
    # On attend une redirection vers /login
    assert response.status_code == 302
