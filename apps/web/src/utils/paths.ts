const BASE_URL = import.meta.env.BASE_URL

export function appPath(path: string): string {
  const normalizedBase = BASE_URL.endsWith('/') ? BASE_URL : `${BASE_URL}/`
  const normalizedPath = path.startsWith('/') ? path.slice(1) : path
  return `${normalizedBase}${normalizedPath}`
}

export function lessonAssetPath(lessonId: string, file: string): string {
  return appPath(`lessons/${lessonId}/${file}`)
}
