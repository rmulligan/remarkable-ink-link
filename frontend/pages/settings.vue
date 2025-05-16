<template>
  <div>
    <h2 class="text-2xl font-bold mb-6">Settings</h2>
    
    <div class="bg-white p-6 rounded-lg shadow">
      <h3 class="text-lg font-semibold mb-4">Authentication</h3>
      
      <!-- reMarkable Credentials -->
      <div class="mb-6">
        <h4 class="font-medium mb-3">reMarkable Credentials</h4>
        <div class="mb-3">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Device Token
          </label>
          <input
            v-model="remarkableToken"
            type="password"
            class="w-full px-3 py-2 border border-gray-300 rounded-md"
            placeholder="Enter your reMarkable device token"
          />
        </div>
        <button
          @click="saveRemarkableAuth"
          :disabled="savingRemarkable"
          class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400"
        >
          {{ savingRemarkable ? 'Saving...' : 'Save reMarkable Auth' }}
        </button>
      </div>
      
      <!-- MyScript Credentials -->
      <div class="mb-6">
        <h4 class="font-medium mb-3">MyScript Credentials</h4>
        <div class="mb-3">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            API Key
          </label>
          <input
            v-model="myscriptKey"
            type="password"
            class="w-full px-3 py-2 border border-gray-300 rounded-md"
            placeholder="Enter your MyScript API key"
          />
        </div>
        <div class="mb-3">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            HMAC Key
          </label>
          <input
            v-model="myscriptHmac"
            type="password"
            class="w-full px-3 py-2 border border-gray-300 rounded-md"
            placeholder="Enter your MyScript HMAC key"
          />
        </div>
        <button
          @click="saveMyscriptAuth"
          :disabled="savingMyscript"
          class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400"
        >
          {{ savingMyscript ? 'Saving...' : 'Save MyScript Auth' }}
        </button>
      </div>
    </div>
    
    <!-- Cloud Upload Settings -->
    <div class="bg-white p-6 rounded-lg shadow mt-6">
      <h3 class="text-lg font-semibold mb-4">Cloud Upload Settings</h3>
      
      <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Upload Folder
        </label>
        <input
          v-model="uploadFolder"
          type="text"
          class="w-full px-3 py-2 border border-gray-300 rounded-md"
          placeholder="/Syntax Highlighted"
        />
      </div>
      
      <div class="mb-4">
        <label class="flex items-center">
          <input
            v-model="autoUpload"
            type="checkbox"
            class="mr-2"
          />
          <span class="text-sm font-medium text-gray-700">
            Automatically upload highlighted notebooks to reMarkable
          </span>
        </label>
      </div>
      
      <button
        @click="saveCloudSettings"
        :disabled="savingCloud"
        class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400"
      >
        {{ savingCloud ? 'Saving...' : 'Save Cloud Settings' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const remarkableToken = ref('')
const myscriptKey = ref('')
const myscriptHmac = ref('')
const uploadFolder = ref('/Syntax Highlighted')
const autoUpload = ref(false)

const savingRemarkable = ref(false)
const savingMyscript = ref(false)
const savingCloud = ref(false)

const config = useRuntimeConfig()

async function loadSettings() {
  try {
    const response = await $fetch(`${config.public.apiBase}/settings`)
    if (response.remarkableToken) remarkableToken.value = response.remarkableToken
    if (response.myscriptKey) myscriptKey.value = response.myscriptKey
    if (response.myscriptHmac) myscriptHmac.value = response.myscriptHmac
    if (response.uploadFolder) uploadFolder.value = response.uploadFolder
    if (response.autoUpload !== undefined) autoUpload.value = response.autoUpload
  } catch (error) {
    console.error('Error loading settings:', error)
  }
}

async function saveRemarkableAuth() {
  savingRemarkable.value = true
  try {
    await $fetch(`${config.public.apiBase}/auth/remarkable`, {
      method: 'POST',
      body: {
        deviceToken: remarkableToken.value
      }
    })
    alert('reMarkable authentication saved successfully!')
  } catch (error) {
    console.error('Error saving reMarkable auth:', error)
    alert('Failed to save reMarkable authentication. Please try again.')
  } finally {
    savingRemarkable.value = false
  }
}

async function saveMyscriptAuth() {
  savingMyscript.value = true
  try {
    await $fetch(`${config.public.apiBase}/auth/myscript`, {
      method: 'POST',
      body: {
        apiKey: myscriptKey.value,
        hmacKey: myscriptHmac.value
      }
    })
    alert('MyScript authentication saved successfully!')
  } catch (error) {
    console.error('Error saving MyScript auth:', error)
    alert('Failed to save MyScript authentication. Please try again.')
  } finally {
    savingMyscript.value = false
  }
}

async function saveCloudSettings() {
  savingCloud.value = true
  try {
    await $fetch(`${config.public.apiBase}/settings/cloud`, {
      method: 'POST',
      body: {
        uploadFolder: uploadFolder.value,
        autoUpload: autoUpload.value
      }
    })
    alert('Cloud settings saved successfully!')
  } catch (error) {
    console.error('Error saving cloud settings:', error)
    alert('Failed to save cloud settings. Please try again.')
  } finally {
    savingCloud.value = false
  }
}

onMounted(() => {
  loadSettings()
})
</script>