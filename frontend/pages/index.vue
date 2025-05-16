<template>
  <div>
    <h2 class="text-2xl font-bold mb-6">Syntax Highlighting</h2>
    
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Code Input Section -->
      <div class="bg-white p-6 rounded-lg shadow">
        <h3 class="text-lg font-semibold mb-4">Code Input</h3>
        
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Select Language
          </label>
          <select v-model="selectedLanguage" class="w-full px-3 py-2 border border-gray-300 rounded-md">
            <option value="javascript">JavaScript</option>
            <option value="python">Python</option>
            <option value="typescript">TypeScript</option>
            <option value="java">Java</option>
            <option value="cpp">C++</option>
          </select>
        </div>
        
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Select Theme
          </label>
          <select v-model="selectedTheme" class="w-full px-3 py-2 border border-gray-300 rounded-md">
            <option value="monokai">Monokai</option>
            <option value="dark">Dark</option>
            <option value="light">Light</option>
          </select>
        </div>
        
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Code
          </label>
          <textarea
            v-model="codeInput"
            class="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
            rows="15"
            placeholder="Paste your code here..."
          ></textarea>
        </div>
        
        <button
          @click="highlightCode"
          :disabled="!codeInput || processing"
          class="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400"
        >
          {{ processing ? 'Processing...' : 'Highlight Code' }}
        </button>
      </div>
      
      <!-- Preview Section -->
      <div class="bg-white p-6 rounded-lg shadow">
        <h3 class="text-lg font-semibold mb-4">Preview</h3>
        
        <div v-if="highlightedResult" class="border border-gray-200 rounded-md p-4">
          <pre v-html="highlightedResult" class="overflow-x-auto"></pre>
        </div>
        
        <div v-else class="text-gray-500 text-center py-8">
          Preview will appear here after highlighting
        </div>
        
        <div v-if="highlightedResult" class="mt-4 flex gap-3">
          <button
            @click="downloadHtml"
            class="flex-1 bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700"
          >
            Download HTML
          </button>
          <button
            @click="downloadHcl"
            class="flex-1 bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700"
          >
            Download HCL
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const codeInput = ref('')
const selectedLanguage = ref('javascript')
const selectedTheme = ref('monokai')
const highlightedResult = ref('')
const processing = ref(false)

const config = useRuntimeConfig()

async function highlightCode() {
  if (!codeInput.value) return
  
  processing.value = true
  try {
    const response = await $fetch(`${config.public.apiBase}/syntax/highlight`, {
      method: 'POST',
      body: {
        code: codeInput.value,
        language: selectedLanguage.value,
        theme: selectedTheme.value
      }
    })
    
    highlightedResult.value = response.html
  } catch (error) {
    console.error('Error highlighting code:', error)
    alert('Failed to highlight code. Please try again.')
  } finally {
    processing.value = false
  }
}

function downloadHtml() {
  const blob = new Blob([highlightedResult.value], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `highlighted-${selectedLanguage.value}.html`
  a.click()
  URL.revokeObjectURL(url)
}

async function downloadHcl() {
  try {
    const response = await $fetch(`${config.public.apiBase}/syntax/highlight`, {
      method: 'POST',
      body: {
        code: codeInput.value,
        language: selectedLanguage.value,
        theme: selectedTheme.value,
        format: 'hcl'
      }
    })
    
    const blob = new Blob([response.hcl], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `highlighted-${selectedLanguage.value}.hcl`
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Error downloading HCL:', error)
    alert('Failed to download HCL. Please try again.')
  }
}
</script>