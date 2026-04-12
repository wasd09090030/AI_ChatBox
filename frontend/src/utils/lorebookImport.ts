/**
 * Lorebook 批量导入工具
 * 支持解析 JSON 格式并导入角色、地点、事件
 */

export interface CharacterData {
  name: string
  age?: number
  gender?: string
  appearance?: string
  personality?: string
  background?: string
}

export interface LocationData {
  name: string
  description: string
  region?: string
  climate?: string
}

export interface EventData {
  name: string
  description: string
  time?: string
  location?: string
}

export interface ParsedLorebookData {
  characters: CharacterData[]
  locations: LocationData[]
  events: EventData[]
}

export interface ImportResult {
  success: boolean
  message: string
  imported: {
    characters: number
    locations: number
    events: number
  }
  errors: string[]
}

/** 功能：函数 asRecord，负责 asRecord 相关处理。 */
function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === 'object') {
    return value as Record<string, unknown>
  }
  return {}
}

/** 功能：函数 asString，负责 asString 相关处理。 */
function asString(value: unknown): string {
  if (value === undefined || value === null) {
    return ''
  }
  return String(value)
}

/** 功能：函数 readErrorDetail，负责 readErrorDetail 相关处理。 */
function readErrorDetail(value: unknown): string {
  const record = asRecord(value)
  if (typeof record.detail === 'string') {
    return record.detail
  }
  if (typeof record.message === 'string') {
    return record.message
  }
  return '未知错误'
}

/**
 * 解析 JSON 字符串为 Lorebook 数据
 */
export function parseLorebookJSON(jsonStr: string): ParsedLorebookData {
  const result: ParsedLorebookData = {
    characters: [],
    locations: [],
    events: []
  }

  try {
    const data = asRecord(JSON.parse(jsonStr))

    // 解析角色
    if (data.characters && Array.isArray(data.characters)) {
      result.characters = data.characters.map((char) => {
        const charRecord = asRecord(char)
        return {
          name: asString(charRecord.name),
          age: charRecord.age ? Number(charRecord.age) : undefined,
          gender: charRecord.gender ? asString(charRecord.gender) : undefined,
          appearance: charRecord.appearance ? asString(charRecord.appearance) : undefined,
          personality: charRecord.personality ? asString(charRecord.personality) : undefined,
          background: charRecord.background ? asString(charRecord.background) : undefined
        }
      }).filter((char: CharacterData) => char.name.trim() !== '')
    }

    // 解析地点
    if (data.locations && Array.isArray(data.locations)) {
      result.locations = data.locations.map((loc) => {
        const locationRecord = asRecord(loc)
        return {
          name: asString(locationRecord.name),
          description: asString(locationRecord.description),
          region: locationRecord.region ? asString(locationRecord.region) : undefined,
          climate: locationRecord.climate ? asString(locationRecord.climate) : undefined
        }
      }).filter((loc: LocationData) => loc.name.trim() !== '' && loc.description.trim() !== '')
    }

    // 解析事件
    if (data.events && Array.isArray(data.events)) {
      result.events = data.events.map((evt) => {
        const eventRecord = asRecord(evt)
        return {
          name: asString(eventRecord.name),
          description: asString(eventRecord.description),
          time: eventRecord.time ? asString(eventRecord.time) : undefined,
          location: eventRecord.location ? asString(eventRecord.location) : undefined
        }
      }).filter((evt: EventData) => evt.name.trim() !== '' && evt.description.trim() !== '')
    }

    return result
  } catch (error) {
    throw new Error('JSON 格式错误: ' + (error as Error).message)
  }
}

/**
 * 批量导入 Lorebook 条目到服务器
 */
export async function importLorebookData(
  worldId: string,
  data: ParsedLorebookData,
  apiBase: string
): Promise<ImportResult> {
  const result: ImportResult = {
    success: true,
    message: '',
    imported: {
      characters: 0,
      locations: 0,
      events: 0
    },
    errors: []
  }

  // 导入角色
  for (const character of data.characters) {
    try {
      const response = await fetch(`${apiBase}/worlds/${worldId}/lorebook/character`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(character)
      })

      if (response.ok) {
        result.imported.characters++
      } else {
        const error = await response.json()
        result.errors.push(`角色 "${character.name}" 导入失败: ${readErrorDetail(error)}`)
      }
    } catch (error) {
      result.errors.push(`角色 "${character.name}" 导入失败: ${(error as Error).message}`)
    }
  }

  // 导入地点
  for (const location of data.locations) {
    try {
      const response = await fetch(`${apiBase}/worlds/${worldId}/lorebook/location`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(location)
      })

      if (response.ok) {
        result.imported.locations++
      } else {
        const error = await response.json()
        result.errors.push(`地点 "${location.name}" 导入失败: ${readErrorDetail(error)}`)
      }
    } catch (error) {
      result.errors.push(`地点 "${location.name}" 导入失败: ${(error as Error).message}`)
    }
  }

  // 导入事件
  for (const event of data.events) {
    try {
      const response = await fetch(`${apiBase}/worlds/${worldId}/lorebook/event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(event)
      })

      if (response.ok) {
        result.imported.events++
      } else {
        const error = await response.json()
        result.errors.push(`事件 "${event.name}" 导入失败: ${readErrorDetail(error)}`)
      }
    } catch (error) {
      result.errors.push(`事件 "${event.name}" 导入失败: ${(error as Error).message}`)
    }
  }

  // 设置结果消息
  const total = result.imported.characters + result.imported.locations + result.imported.events
  if (total === 0) {
    result.success = false
    result.message = '导入失败，没有成功导入任何条目'
  } else if (result.errors.length > 0) {
    result.success = true
    result.message = `部分导入成功：${total} 个条目成功，${result.errors.length} 个失败`
  } else {
    result.success = true
    result.message = `导入成功！共导入 ${total} 个条目`
  }

  return result
}

/**
 * 生成 JSON 模板示例
 */
export function getJSONTemplate(): string {
  const template = {
    characters: [
      {
        name: "张三",
        age: 25,
        gender: "男",
        appearance: "身材高大，留着短发",
        personality: "勇敢果断，有些冲动",
        background: "来自北方的战士"
      }
    ],
    locations: [
      {
        name: "暗影森林",
        description: "一片终年被迷雾笼罩的古老森林",
        region: "北境",
        climate: "阴冷潮湿"
      }
    ],
    events: [
      {
        name: "龙的苏醒",
        description: "沉睡千年的巨龙从火山中苏醒",
        time: "三年前",
        location: "火焰山"
      }
    ]
  }

  return JSON.stringify(template, null, 2)
}

/**
 * 验证 JSON 格式是否正确
 */
export function validateLorebookJSON(jsonStr: string): { valid: boolean; error?: string } {
  try {
    const data = JSON.parse(jsonStr)
    
    // 检查是否至少有一个类型的数据
    const hasCharacters = data.characters && Array.isArray(data.characters) && data.characters.length > 0
    const hasLocations = data.locations && Array.isArray(data.locations) && data.locations.length > 0
    const hasEvents = data.events && Array.isArray(data.events) && data.events.length > 0

    if (!hasCharacters && !hasLocations && !hasEvents) {
      return {
        valid: false,
        error: 'JSON 中没有有效的数据。请确保包含 characters、locations 或 events 数组'
      }
    }

    return { valid: true }
  } catch (error) {
    return {
      valid: false,
      error: 'JSON 格式错误: ' + (error as Error).message
    }
  }
}
