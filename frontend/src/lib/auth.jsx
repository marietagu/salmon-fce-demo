import React from 'react'
import { Auth0Provider, useAuth0 } from '@auth0/auth0-react'

export const AuthProvider = ({ children }) => (
  <Auth0Provider
    domain={import.meta.env.VITE_AUTH0_DOMAIN}
    clientId={import.meta.env.VITE_AUTH0_CLIENT_ID}
    authorizationParams={{
      audience: import.meta.env.VITE_AUTH0_AUDIENCE,
      redirect_uri: window.location.origin,
    }}
    cacheLocation="localstorage"
  >
    {children}
  </Auth0Provider>
)

export const useToken = () => {
  const { getAccessTokenSilently } = useAuth0()
  return async () => {
    if (!import.meta.env.VITE_AUTH0_DOMAIN) return null
    try { return await getAccessTokenSilently() } catch { return null }
  }
}

