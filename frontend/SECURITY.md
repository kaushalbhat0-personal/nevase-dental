# Security Considerations

## Current Implementation Notes

### Token Storage (localStorage)

**Current Status:** The application currently stores JWT tokens in `localStorage`.

**Risk:** This approach is vulnerable to XSS (Cross-Site Scripting) attacks. If an attacker can inject malicious JavaScript into the application, they can access the token from `localStorage`.

**Recommended Solution:** Migrate to httpOnly cookies for production deployments.

#### Migration Path to httpOnly Cookies

1. **Backend Changes:**
   - Set JWT token in an httpOnly, secure, sameSite cookie during login
   - Remove the token from the response body
   - Implement token refresh mechanism via httpOnly cookie

2. **Frontend Changes:**
   - Remove `localStorage.getItem('token')` calls
   - Update API interceptors to rely on automatic cookie sending
   - Remove manual token management in `useAuth.ts`
   - Update `api.ts` request interceptor to remove Authorization header (cookies are sent automatically)

#### Implementation Example (Backend - FastAPI):

```python
from fastapi import Response

@router.post("/login")
async def login(response: Response, credentials: LoginCredentials):
    # ... authenticate user ...
    token = create_access_token(user.id)
    
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,  # HTTPS only
        samesite="strict",
        max_age=3600  # 1 hour
    )
    return {"user": user}
```

#### Implementation Example (Frontend):

```typescript
// api.ts - Remove Authorization header, cookies auto-sent
api.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
);

// useAuth.ts - No manual token storage
const login = useCallback(async (credentials) => {
  const response = await authApi.login(credentials);
  setUser(response.user);
}, []);
```

### Additional Security Recommendations

1. **CSRF Protection:** Implement CSRF tokens when using cookies
2. **Rate Limiting:** Add rate limiting on login endpoints
3. **Password Policy:** Enforce strong password requirements
4. **Session Management:** Implement session timeout and concurrent session limits
5. **HTTPS:** Ensure all communications use HTTPS in production
