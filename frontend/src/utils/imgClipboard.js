import * as caseApi from '@/api/case'

async function fileToMd5(file) {
  const buffer = await file.arrayBuffer()
  const hashBuffer = await crypto.subtle.digest('MD5', buffer)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
}

function base64ToFile(base64) {
  const arr = base64.split(',')
  const mime = arr[0].match(/:(.*?);/)[1]
  const bstr = atob(arr[1])
  let n = bstr.length
  const u8arr = new Uint8Array(n)
  while (n--) {
    u8arr[n] = bstr.charCodeAt(n)
  }
  const ext = mime.split('/')[1] || 'png'
  return new File([u8arr], `image.${ext}`, { type: mime })
}

async function uploadSingleAsset(file, mapId, nodeId) {
  const fileHash = await fileToMd5(file)
  const checkRes = await caseApi.checkHash({ map_id: mapId, file_hash: fileHash })
  if (checkRes?.url) {
    return { url: checkRes.url }
  }

  const formData = new FormData()
  formData.append('map_id', mapId)
  formData.append('node_id', nodeId || '')
  formData.append('file_hash', fileHash)
  formData.append('file', file)
  return caseApi.uploadAsset(formData)
}

export async function uploadImgMapAndClean(mindMap, mapId) {
  const root = mindMap.getData(false)
  const updates = []

  function walk(node) {
    const data = node.data || {}
    if (data.image && data.image.startsWith('data:image')) {
      updates.push({ node, key: 'image' })
    }
    if (data.imgMap) {
      Object.entries(data.imgMap).forEach(([key, url]) => {
        if (url.startsWith('data:image')) {
          updates.push({ node, key, isImgMap: true })
        }
      })
    }
    node.children?.forEach(walk)
  }

  walk(root)

  for (const item of updates) {
    const data = item.node.data
    const base64 = item.isImgMap ? data.imgMap[item.key] : data.image
    const file = base64ToFile(base64)
    const asset = await uploadSingleAsset(file, mapId, data.uid || '')
    if (item.isImgMap) {
      data.imgMap[item.key] = asset.url
    } else {
      data.image = asset.url
    }
  }

  mindMap.setData(root)
  return root
}
