export const TOKEN_KEY = 'laboratory-booking-token'
export const USER_KEY = 'laboratory-booking-user'

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}
