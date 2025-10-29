<template>
  <div class="quiz-container">
    <div v-if="isLoading" class="loading">Loading Quiz...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>

    <div v-else-if="!showResults">
      <h1>{{ quiz.quiz_title }}</h1>
      <div class="question-card">
        <h2>Question {{ currentQuestionIndex + 1 }} of {{ quiz.questions.length }}</h2>
        <p class="question-text">{{ currentQuestion.question }}</p>
        <div class="options-container">
          <div v-for="(option, index) in currentQuestion.options" :key="index" class="option" 
               :class="{ selected: selectedAnswer === option }" @click="selectAnswer(option)">
            {{ option }}
          </div>
        </div>
      </div>
      <button @click="nextQuestion" :disabled="!selectedAnswer" class="btn-next">
        {{ isLastQuestion ? 'Submit Quiz' : 'Next Question' }}
      </button>
    </div>

    <div v-else class="results-container">
      <h1>Quiz Results</h1>
      <h2>Your Score: {{ results.score }} / {{ results.max_score }} ({{ scorePercentage }}%)</h2>
      <div v-for="(question, index) in quiz.questions" :key="index" class="result-item"
           :class="{ correct: studentAnswers[index].answer === results.correct_answers[index] }">
        <p><strong>Q: {{ question.question }}</strong></p>
        <p>Your Answer: {{ studentAnswers[index].answer }}</p>
        <p>Correct Answer: {{ results.correct_answers[index] }}</p>
      </div>
      <RouterLink to="/dashboard" class="btn-back">Back to Dashboard</RouterLink>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter, RouterLink } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import axios from 'axios';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const quiz = ref(null);
const isLoading = ref(true);
const error = ref('');
const currentQuestionIndex = ref(0);
const selectedAnswer = ref(null);
const studentAnswers = ref([]);
const showResults = ref(false);
const results = ref(null);

const apiClient = axios.create({
  baseURL: 'http://localhost:5000/api',
  headers: { Authorization: `Bearer ${authStore.token}` }
});

const currentQuestion = computed(() => quiz.value?.questions[currentQuestionIndex.value]);
const isLastQuestion = computed(() => currentQuestionIndex.value === quiz.value?.questions.length - 1);
const scorePercentage = computed(() => results.value ? Math.round((results.value.score / results.value.max_score) * 100) : 0);

const fetchQuiz = async () => {
  try {
    const response = await apiClient.get(`/quizzes/${route.params.contentId}`);
    quiz.value = response.data;
  } catch (err) {
    error.value = 'Failed to load the quiz.';
  } finally {
    isLoading.value = false;
  }
};

const selectAnswer = (option) => {
  selectedAnswer.value = option;
};

const nextQuestion = async () => {
  // Record the answer
  studentAnswers.value.push({
    questionId: currentQuestion.value.id,
    answer: selectedAnswer.value
  });

  if (isLastQuestion.value) {
    await submitQuiz();
  } else {
    currentQuestionIndex.value++;
    selectedAnswer.value = null; // Reset for next question
  }
};

const submitQuiz = async () => {
  isLoading.value = true;
  try {
    const response = await apiClient.post(`/quizzes/${route.params.contentId}/submit`, {
      answers: studentAnswers.value
    });
    results.value = response.data;
    showResults.value = true;
  } catch (err) {
    error.value = 'Failed to submit quiz results.';
  } finally {
    isLoading.value = false;
  }
};

onMounted(fetchQuiz);
</script>

<style scoped>
.quiz-container { max-width: 800px; margin: 2rem auto; padding: 1rem; }
.question-card { background: #fff; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.question-text { font-size: 1.5rem; margin-bottom: 2rem; }
.options-container { display: flex; flex-direction: column; gap: 1rem; }
.option { padding: 1rem; border: 1px solid #ccc; border-radius: 5px; cursor: pointer; transition: all 0.2s; }
.option:hover { background-color: #f8f9fa; }
.option.selected { background-color: #007bff; color: white; border-color: #0056b3; }
.btn-next { width: 100%; margin-top: 1.5rem; padding: 1rem; font-size: 1.2rem; background-color: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; }
.btn-next:disabled { background-color: #ccc; cursor: not-allowed; }

.results-container { text-align: center; }
.result-item { background: #f8f9fa; border-left: 5px solid #dc3545; text-align: left; padding: 1rem; margin-bottom: 1rem; border-radius: 5px; }
.result-item.correct { border-left-color: #28a745; }
.btn-back { display: inline-block; margin-top: 2rem; padding: 0.8rem 2rem; background-color: #6c757d; color: white; text-decoration: none; border-radius: 5px; }
.loading, .error-message { text-align: center; padding: 3rem; font-size: 1.2rem; }
</style>