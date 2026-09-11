import { api } from './api'

export interface BusinessType {
  public_id: string
  name: string
  slug: string
  description: string | null
  icon: string | null
}

export async function getBusinessTypes(): Promise<BusinessType[]> {
  const { data } = await api.get<{ items: BusinessType[] }>('/business-types')
  return data.items
}
