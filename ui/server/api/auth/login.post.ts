import { z } from 'zod'

const bodySchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1),
})

export default defineEventHandler(async (event) => {
  const { username, password } = await readValidatedBody(event, bodySchema.parse)

  const config = useRuntimeConfig(event)

  if (username !== config.adminUser || password !== config.adminPassword) {
    throw createError({ statusCode: 401, message: 'Invalid credentials' })
  }

  await setUserSession(event, {
    user: { name: username },
  })

  return { ok: true }
})
