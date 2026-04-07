/**
 * 文件解析服务
 * 
 * 纯前端实现文件内容提取，支持：
 * - 文本文件 (.txt, .md, .json, .csv, .xml, .html, .css, .js, .ts, .py 等)
 * - PDF 文件 (需要 pdf.js)
 * - Word 文档 (需要 mammoth.js)
 * - Excel 文件 (需要 read-excel-file)
 * - 图片 OCR (需要 tesseract.js 或转 base64 发送给支持视觉的 API)
 */

// 支持的文件类型
export const SUPPORTED_FILE_TYPES = {
  text: ['.txt', '.md', '.json', '.csv', '.xml', '.html', '.css', '.js', '.ts', '.py', '.java', '.c', '.cpp', '.h', '.go', '.rs', '.sql', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.log'],
  pdf: ['.pdf'],
  word: ['.docx'],
  excel: ['.xlsx', '.xls'],
  image: ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']
}

export interface ParsedFile {
  name: string
  type: string
  size: number
  content: string
  encoding?: string
  error?: string
}

export interface FileParserOptions {
  maxSize?: number // 最大文件大小 (bytes)，默认 10MB
  maxTextLength?: number // 最大文本长度，默认 100000 字符
}

const DEFAULT_OPTIONS: FileParserOptions = {
  maxSize: 10 * 1024 * 1024, // 10MB
  maxTextLength: 100000
}

/**
 * 获取文件扩展名
 */
function getFileExtension(filename: string): string {
  const ext = filename.toLowerCase().match(/\.[^.]+$/)
  return ext ? ext[0] : ''
}

/**
 * 判断文件类型
 */
export function getFileType(filename: string): 'text' | 'pdf' | 'word' | 'excel' | 'image' | 'unknown' {
  const ext = getFileExtension(filename)
  
  for (const [type, extensions] of Object.entries(SUPPORTED_FILE_TYPES)) {
    if (extensions.includes(ext)) {
      return type as 'text' | 'pdf' | 'word' | 'excel' | 'image'
    }
  }
  return 'unknown'
}

/**
 * 解析文本文件
 */
async function parseTextFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const content = e.target?.result as string
      resolve(content)
    }
    reader.onerror = () => reject(new Error('读取文本文件失败'))
    reader.readAsText(file, 'UTF-8')
  })
}

/**
 * 解析 CSV 文件为可读格式
 */
async function parseCSVFile(file: File): Promise<string> {
  const text = await parseTextFile(file)
  const lines = text.split('\n')
  const result: string[] = []
  
  for (const line of lines) {
    if (line.trim()) {
      result.push(line)
    }
  }
  
  return `CSV 文件内容 (${lines.length} 行):\n${result.join('\n')}`
}

/**
 * 解析 JSON 文件为格式化文本
 */
async function parseJSONFile(file: File): Promise<string> {
  const text = await parseTextFile(file)
  try {
    const parsed = JSON.parse(text)
    return `JSON 文件内容:\n${JSON.stringify(parsed, null, 2)}`
  } catch {
    return `JSON 文件内容 (原始):\n${text}`
  }
}

/**
 * 将图片转换为 Base64
 * 注意：DeepSeek 不支持图片，但可以用于其他支持 Vision 的 API
 */
export async function imageToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const base64 = e.target?.result as string
      resolve(base64)
    }
    reader.onerror = () => reject(new Error('读取图片文件失败'))
    reader.readAsDataURL(file)
  })
}

/**
 * 解析 PDF 文件 (需要安装 pdfjs-dist)
 * 
 * 使用方法：
 * 1. npm install pdfjs-dist
 * 2. 取消下面的注释
 */
async function parsePDFFile(file: File): Promise<string> {
  // 动态导入 pdf.js
  try {
    const pdfjsLib = await import('pdfjs-dist')
    
    // 设置 worker
    pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`
    
    const arrayBuffer = await file.arrayBuffer()
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
    
    const textParts: string[] = []
    
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i)
      const textContent = await page.getTextContent()
      const pageText = textContent.items
        .map((item) => ('str' in item ? item.str : ''))
        .join(' ')
      textParts.push(`[第 ${i} 页]\n${pageText}`)
    }
    
    return `PDF 文件内容 (共 ${pdf.numPages} 页):\n\n${textParts.join('\n\n')}`
  } catch {
    // 如果 pdfjs-dist 未安装，返回提示
    return `[PDF 解析需要安装 pdfjs-dist 库]\n请运行: npm install pdfjs-dist\n\n文件名: ${file.name}\n文件大小: ${(file.size / 1024).toFixed(2)} KB`
  }
}

/**
 * 解析 Word 文档 (需要安装 mammoth)
 * 
 * 使用方法：
 * 1. npm install mammoth
 * 2. 取消下面的注释
 */
async function parseWordFile(file: File): Promise<string> {
  try {
    const mammoth = await import('mammoth')
    const arrayBuffer = await file.arrayBuffer()
    const result = await mammoth.extractRawText({ arrayBuffer })
    return `Word 文档内容:\n\n${result.value}`
  } catch {
    return `[Word 解析需要安装 mammoth 库]\n请运行: npm install mammoth\n\n文件名: ${file.name}\n文件大小: ${(file.size / 1024).toFixed(2)} KB`
  }
}

/**
 * 解析 Excel 文件 (需要安装 read-excel-file)
 * 
 * 使用方法：
 * 1. npm install read-excel-file
 * 2. 取消下面的注释
 */
async function parseExcelFile(file: File): Promise<string> {
  try {
    const { default: readXlsxFile, readSheetNames } = await import('read-excel-file')
    const sheetNames = await readSheetNames(file)
    
    const result: string[] = []
    
    for (const sheetName of sheetNames) {
      const rows = await readXlsxFile(file, { sheet: sheetName })
      const csvRows = rows.map((row) =>
        row.map((cell) => (cell === null || cell === undefined ? '' : String(cell))).join(',')
      )
      result.push(`[工作表: ${sheetName}]\n${csvRows.join('\n')}`)
    }
    
    return `Excel 文件内容 (共 ${sheetNames.length} 个工作表):\n\n${result.join('\n\n')}`
  } catch {
    return `[Excel 解析需要安装 read-excel-file 库]\n请运行: npm install read-excel-file\n\n文件名: ${file.name}\n文件大小: ${(file.size / 1024).toFixed(2)} KB`
  }
}

/**
 * 主解析函数 - 根据文件类型自动选择解析方法
 */
export async function parseFile(file: File, options: FileParserOptions = {}): Promise<ParsedFile> {
  const opts = { ...DEFAULT_OPTIONS, ...options }
  
  // 检查文件大小
  if (file.size > opts.maxSize!) {
    return {
      name: file.name,
      type: file.type,
      size: file.size,
      content: '',
      error: `文件过大，最大支持 ${(opts.maxSize! / 1024 / 1024).toFixed(1)} MB`
    }
  }
  
  const fileType = getFileType(file.name)
  const ext = getFileExtension(file.name)
  
  let content: string
  
  try {
    switch (fileType) {
      case 'text':
        if (ext === '.csv') {
          content = await parseCSVFile(file)
        } else if (ext === '.json') {
          content = await parseJSONFile(file)
        } else {
          content = await parseTextFile(file)
        }
        break
      
      case 'pdf':
        content = await parsePDFFile(file)
        break
      
      case 'word':
        content = await parseWordFile(file)
        break
      
      case 'excel':
        content = await parseExcelFile(file)
        break
      
      case 'image':
        // DeepSeek 不支持图片，返回提示信息
        content = `[图片文件: ${file.name}]\n\nDeepSeek API 目前不支持图片/多模态输入。\n\n如需处理图片，请考虑：\n1. 使用 OpenAI GPT-4 Vision\n2. 使用 Anthropic Claude Vision\n3. 使用前端 OCR 库 (tesseract.js) 提取文字`
        break
      
      default:
        content = `[不支持的文件类型: ${ext}]\n\n文件名: ${file.name}\n文件大小: ${(file.size / 1024).toFixed(2)} KB`
    }
    
    // 截断过长的内容
    if (content.length > opts.maxTextLength!) {
      content = content.substring(0, opts.maxTextLength!) + 
        `\n\n...[内容已截断，原始长度: ${content.length} 字符]`
    }
    
    return {
      name: file.name,
      type: file.type || fileType,
      size: file.size,
      content
    }
  } catch (error) {
    return {
      name: file.name,
      type: file.type,
      size: file.size,
      content: '',
      error: error instanceof Error ? error.message : '解析文件时发生未知错误'
    }
  }
}

/**
 * 批量解析多个文件
 */
export async function parseFiles(files: File[], options: FileParserOptions = {}): Promise<ParsedFile[]> {
  const results = await Promise.all(
    Array.from(files).map(file => parseFile(file, options))
  )
  return results
}

/**
 * 将解析后的文件内容格式化为适合发送给 AI 的提示词
 */
export function formatFilesForPrompt(parsedFiles: ParsedFile[]): string {
  if (parsedFiles.length === 0) return ''
  
  const parts = parsedFiles.map((file, index) => {
    if (file.error) {
      return `【文件 ${index + 1}: ${file.name}】\n错误: ${file.error}`
    }
    return `【文件 ${index + 1}: ${file.name}】\n${file.content}`
  })
  
  return `以下是用户上传的文件内容：\n\n${parts.join('\n\n---\n\n')}\n\n---\n\n请根据以上文件内容回答用户的问题。`
}
