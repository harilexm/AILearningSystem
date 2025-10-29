<template>
  <div class="course-detail-container">
    <div v-if="isLoading" class="loading">Loading course details...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    
    <div v-else-if="course">
      <h1 class="course-title">{{ course.title }}</h1>
      <p class="course-description">{{ course.description }}</p>
      
      <div v-for="module in course.modules" :key="module.id" class="module-container">
        <h2>{{ module.title }}</h2>
        <ul class="content-list">
          <li v-for="content in module.learning_contents" :key="content.id" class="content-item">
            <span class="content-type-icon">{{ getIconFor(content.type) }}</span>
            <div class="content-info">
              <span class="content-title">{{ content.title }}</span>
              <a v-if="content.url" :href="content.url" target="_blank" class="content-link">Go to Content &rarr;</a>
              <!-- DYNAMIC LINKING LOGIC -->
              <a v-if="content.type === 'video' && content.url" :href="content.url" target="_blank" class="content-link">
                Watch Video &rarr;
              </a>
              <RouterLink v-else-if="content.type === 'quiz'" :to="{ name: 'take-quiz', params: { contentId: content.id } }" class="content-link">
                Start Quiz &rarr;
              </RouterLink>
              <span v-else-if="content.type === 'article'" class="content-link-placeholder">
                (Article content will show here)
              </span>
            </div>
            <!-- INTERACTION BUTTON -->
            <div class="content-action">
              <button v-if="content.progress_status !== 'completed'" @click="markAsComplete(content.id)" class="btn-complete">
                Mark as Complete
              </button>
              <span v-else class="status-completed">
                Completed ✔️
              </span>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import axios from 'axios';

const route = useRoute();
const authStore = useAuthStore();
const course = ref(null);
const isLoading = ref(true);
const error = ref('');

const apiClient = axios.create({
  baseURL: 'http://localhost:5000/api',
  headers: { Authorization: `Bearer ${authStore.token}` }
});

const fetchCourseDetails = async () => {
  const courseId = route.params.courseId;
  try {
    const response = await apiClient.get(`/courses/${courseId}`);
    course.value = response.data;
  } catch (err) { error.value = 'Failed to load course details.'; } 
  finally { isLoading.value = false; }
};

// --- NEW FUNCTION ---
const markAsComplete = async (contentId) => {
  try {
    await apiClient.post(`/progress/${contentId}/complete`);
    // Find the content item in our local state and update it
    // This provides an instant UI update without a full page reload.
    for (const module of course.value.modules) {
      const contentItem = module.learning_contents.find(c => c.id === contentId);
      if (contentItem) {
        contentItem.progress_status = 'completed';
        break; // Stop searching once found
      }
    }
  } catch (err) {
    alert('Could not update progress. Please try again.');
  }
};

const getIconFor = (type) => {
  if (type === 'video') return '▶️';
  if (type === 'article') return '📄';
  return '🔗';
};

onMounted(fetchCourseDetails);
</script>

<style scoped>
/* ... (keep all existing styles) ... */
.content-item {
  display: flex;
  align-items: center;
  padding: 1rem 0;
  border-bottom: 1px solid #f1f1f1;
}
.content-info { flex-grow: 1; }
/* --- NEW STYLES --- */
.content-action { margin-left: auto; }
.btn-complete {
  background-color: #007bff;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 5px;
  cursor: pointer;
  font-weight: 500;
}
.btn-complete:hover { background-color: #0056b3; }
.status-completed {
  color: #28a745;
  font-weight: bold;
  padding: 0.5rem 1rem;
}
/* All other styles from the previous step are correct */
.course-detail-container { max-width: 900px; margin: 2rem auto; padding: 1rem; }
.course-title { font-size: 2.5rem; margin-bottom: 0.5rem; }
.course-description { font-size: 1.1rem; color: #6c757d; margin-bottom: 3rem; }
.module-container { background: #fff; border-radius: 8px; padding: 1.5rem 2rem; margin-bottom: 2rem; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.module-container h2 { margin-top: 0; border-bottom: 1px solid #eee; padding-bottom: 1rem; }
.content-list { list-style: none; padding: 0; }
.content-item:last-child { border-bottom: none; }
.content-type-icon { font-size: 1.5rem; margin-right: 1.5rem; }
.content-title { font-weight: 500; display: block; }
.content-link { font-size: 0.9rem; color: #007bff; text-decoration: none; font-weight: bold; }
.error-message, .loading { text-align: center; font-size: 1.2rem; padding: 2rem; }
</style>