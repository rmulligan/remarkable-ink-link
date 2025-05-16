<template>
  <div>
    <h2 class="text-2xl font-bold mb-6">Theme Management</h2>
    
    <!-- Upload New Theme -->
    <div class="bg-white p-6 rounded-lg shadow mb-6">
      <h3 class="text-lg font-semibold mb-4">Upload Custom Theme</h3>
      
      <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Theme Name
        </label>
        <input
          v-model="newThemeName"
          type="text"
          class="w-full px-3 py-2 border border-gray-300 rounded-md"
          placeholder="Enter theme name"
        />
      </div>
      
      <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Theme File (JSON)
        </label>
        <input
          type="file"
          @change="handleFileUpload"
          accept=".json"
          class="w-full px-3 py-2 border border-gray-300 rounded-md"
        />
      </div>
      
      <div v-if="themePreview" class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Theme Preview
        </label>
        <pre class="bg-gray-100 p-3 rounded-md text-sm overflow-x-auto">{{ themePreview }}</pre>
      </div>
      
      <button
        @click="uploadTheme"
        :disabled="!newThemeName || !selectedFile || uploading"
        class="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400"
      >
        {{ uploading ? 'Uploading...' : 'Upload Theme' }}
      </button>
    </div>
    
    <!-- Available Themes -->
    <div class="bg-white p-6 rounded-lg shadow">
      <h3 class="text-lg font-semibold mb-4">Available Themes</h3>
      
      <div v-if="loading" class="text-center py-4">
        Loading themes...
      </div>
      
      <div v-else-if="themes.length === 0" class="text-center py-4 text-gray-500">
        No themes available
      </div>
      
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="theme in themes"
          :key="theme.name"
          class="border border-gray-200 rounded-lg p-4"
        >
          <h4 class="font-semibold mb-2">{{ theme.name }}</h4>
          <p class="text-sm text-gray-600 mb-3">{{ theme.isBuiltIn ? 'Built-in' : 'Custom' }}</p>
          
          <div class="flex gap-2">
            <button
              @click="previewTheme(theme)"
              class="flex-1 bg-gray-200 text-gray-800 px-3 py-1 rounded-md hover:bg-gray-300 text-sm"
            >
              Preview
            </button>
            <button
              v-if="!theme.isBuiltIn"
              @click="deleteTheme(theme)"
              class="flex-1 bg-red-600 text-white px-3 py-1 rounded-md hover:bg-red-700 text-sm"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const themes = ref([])
const loading = ref(true)
const newThemeName = ref('')
const selectedFile = ref(null)
const themePreview = ref('')
const uploading = ref(false)

const config = useRuntimeConfig()

async function fetchThemes() {
  loading.value = true
  try {
    const response = await $fetch(`${config.public.apiBase}/syntax/themes`)
    themes.value = response.themes
  } catch (error) {
    console.error('Error fetching themes:', error)
  } finally {
    loading.value = false
  }
}

function handleFileUpload(event) {
  const file = event.target.files[0]
  if (!file) return
  
  selectedFile.value = file
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const content = JSON.parse(e.target.result)
      themePreview.value = JSON.stringify(content, null, 2)
    } catch (error) {
      alert('Invalid JSON file')
      selectedFile.value = null
      themePreview.value = ''
    }
  }
  reader.readAsText(file)
}

async function uploadTheme() {
  if (!newThemeName.value || !selectedFile.value) return
  
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('name', newThemeName.value)
    formData.append('file', selectedFile.value)
    
    await $fetch(`${config.public.apiBase}/syntax/themes`, {
      method: 'POST',
      body: formData
    })
    
    alert('Theme uploaded successfully!')
    newThemeName.value = ''
    selectedFile.value = null
    themePreview.value = ''
    await fetchThemes()
  } catch (error) {
    console.error('Error uploading theme:', error)
    alert('Failed to upload theme. Please try again.')
  } finally {
    uploading.value = false
  }
}

async function deleteTheme(theme) {
  if (!confirm(`Are you sure you want to delete the theme "${theme.name}"?`)) return
  
  try {
    await $fetch(`${config.public.apiBase}/syntax/themes/${theme.name}`, {
      method: 'DELETE'
    })
    
    alert('Theme deleted successfully!')
    await fetchThemes()
  } catch (error) {
    console.error('Error deleting theme:', error)
    alert('Failed to delete theme. Please try again.')
  }
}

function previewTheme(theme) {
  // TODO: Implement theme preview functionality
  alert(`Preview for ${theme.name} coming soon!`)
}

onMounted(() => {
  fetchThemes()
})
</script>