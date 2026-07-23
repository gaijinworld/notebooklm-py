import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, browserLocalPersistence, setPersistence } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: 'AIzaSyAr5oe2DNaYQseh2iYPvBucZvibKyqNLOc',
  authDomain: 'gamified-network-engineer-app.firebaseapp.com',
  projectId: 'gamified-network-engineer-app',
  storageBucket: 'gamified-network-engineer-app.firebasestorage.app',
  messagingSenderId: '465331311664',
  appId: '1:465331311664:web:d558dfc8f83e81edcf89f5',
  measurementId: 'G-DCFM1RVPP5',
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export const googleProvider = new GoogleAuthProvider();

googleProvider.addScope('profile');
googleProvider.addScope('email');

setPersistence(auth, browserLocalPersistence).catch((err) => {
  console.warn('Failed to set Firebase persistence:', err);
});
