import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
  Animated,
  Dimensions,
  StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import AsyncStorage from '@react-native-async-storage/async-storage';

const { width } = Dimensions.get('window');

const AGE_TIERS = [
  { value: '4-6', label: '4-6 years', emoji: '🧒', desc: 'Preschool', color: '#FF6B6B', bg: '#FFE8E8' },
  { value: '7-9', label: '7-9 years', emoji: '👧', desc: 'Early Elementary', color: '#4ECDC4', bg: '#E0F7F5' },
  { value: '10-12', label: '10-12 years', emoji: '🧑', desc: 'Upper Elementary', color: '#FFD93D', bg: '#FFF8E0' },
  { value: '13-18', label: '13-18 years', emoji: '🎓', desc: 'Teen', color: '#6C5CE7', bg: '#EDE9FE' },
];

export default function OnboardingScreen() {
  const [step, setStep] = useState(1);
  const [childName, setChildName] = useState('');
  const [selectedAgeTier, setSelectedAgeTier] = useState('');
  const [consentGiven, setConsentGiven] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(30)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, { toValue: 1, duration: 500, useNativeDriver: true }),
      Animated.timing(slideAnim, { toValue: 0, duration: 500, useNativeDriver: true }),
    ]).start();
  }, [step]);

  const handleContinue = async () => {
    fadeAnim.setValue(0);
    slideAnim.setValue(30);
    
    if (step === 1) {
      if (!childName.trim()) {
        Alert.alert('Oops!', "Please enter your child's name 😊");
        return;
      }
      setStep(2);
    } else if (step === 2) {
      if (!selectedAgeTier) {
        Alert.alert('One more thing!', 'Please select an age group 🎂');
        return;
      }
      setStep(3);
    } else if (step === 3) {
      if (!consentGiven) {
        Alert.alert('Consent Required', 'Please provide parental consent to continue ✅');
        return;
      }
      await createChildProfile();
    }
  };

  const createChildProfile = async () => {
    setIsLoading(true);
    try {
      const childId = `child_${Date.now()}`;
      const childData = {
        child_id: childId,
        name: childName,
        age_tier: selectedAgeTier,
        parental_consent_given: true,
      };
      
      await AsyncStorage.setItem('currentChild', JSON.stringify(childData));
      await AsyncStorage.setItem('childId', childId);
      await AsyncStorage.setItem('ageTier', selectedAgeTier);
      
      router.replace('/chat');
    } catch (error) {
      Alert.alert('Error', 'Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const selectedTier = AGE_TIERS.find(t => t.value === selectedAgeTier);

  const renderStep1 = () => (
    <Animated.View style={[styles.stepContent, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}>
      <View style={styles.stepHeader}>
        <View style={styles.emojiCircle}>
          <Text style={styles.headerEmoji}>👋</Text>
        </View>
        <Text style={styles.stepTitle}>Welcome to Bible Buddy!</Text>
        <Text style={styles.stepSubtitle}>Let's get to know your child</Text>
      </View>
      
      <View style={styles.inputSection}>
        <Text style={styles.inputLabel}>What's your child's name?</Text>
        <View style={styles.inputContainer}>
          <Ionicons name="person" size={22} color="#6C5CE7" style={styles.inputIcon} />
          <TextInput
            style={styles.textInput}
            value={childName}
            onChangeText={setChildName}
            placeholder="Enter name here..."
            placeholderTextColor="#AAA"
            autoFocus
          />
        </View>
      </View>
    </Animated.View>
  );

  const renderStep2 = () => (
    <Animated.View style={[styles.stepContent, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}>
      <View style={styles.stepHeader}>
        <View style={[styles.emojiCircle, { backgroundColor: '#FFF8E0' }]}>
          <Text style={styles.headerEmoji}>🎂</Text>
        </View>
        <Text style={styles.stepTitle}>Hi, {childName}! 👋</Text>
        <Text style={styles.stepSubtitle}>What age group fits best?</Text>
      </View>
      
      <View style={styles.ageGrid}>
        {AGE_TIERS.map((tier) => (
          <TouchableOpacity
            key={tier.value}
            style={[
              styles.ageCard,
              { backgroundColor: tier.bg, borderColor: selectedAgeTier === tier.value ? tier.color : 'transparent' },
            ]}
            onPress={() => setSelectedAgeTier(tier.value)}
            activeOpacity={0.8}
          >
            <Text style={styles.ageEmoji}>{tier.emoji}</Text>
            <Text style={[styles.ageLabel, { color: tier.color }]}>{tier.label}</Text>
            <Text style={styles.ageDesc}>{tier.desc}</Text>
            {selectedAgeTier === tier.value && (
              <View style={[styles.checkBadge, { backgroundColor: tier.color }]}>
                <Ionicons name="checkmark" size={16} color="#fff" />
              </View>
            )}
          </TouchableOpacity>
        ))}
      </View>
    </Animated.View>
  );

  const renderStep3 = () => (
    <Animated.View style={[styles.stepContent, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}>
      <View style={styles.stepHeader}>
        <View style={[styles.emojiCircle, { backgroundColor: '#E0F7F5' }]}>
          <Text style={styles.headerEmoji}>🛡️</Text>
        </View>
        <Text style={styles.stepTitle}>Safety First!</Text>
        <Text style={styles.stepSubtitle}>We keep your child protected</Text>
      </View>
      
      <View style={styles.safetyCard}>
        {[
          { icon: 'shield-checkmark', color: '#4ECDC4', text: 'Age-appropriate content only' },
          { icon: 'eye-off', color: '#6C5CE7', text: 'No personal data collection' },
          { icon: 'lock-closed', color: '#FF6B6B', text: 'Safety filters always on' },
          { icon: 'people', color: '#FFD93D', text: 'Parent dashboard access' },
        ].map((item, i) => (
          <View key={i} style={styles.safetyItem}>
            <View style={[styles.safetyIconCircle, { backgroundColor: `${item.color}20` }]}>
              <Ionicons name={item.icon as any} size={22} color={item.color} />
            </View>
            <Text style={styles.safetyText}>{item.text}</Text>
          </View>
        ))}
      </View>
      
      <TouchableOpacity style={styles.consentBox} onPress={() => setConsentGiven(!consentGiven)} activeOpacity={0.8}>
        <View style={[styles.checkbox, consentGiven && styles.checkboxChecked]}>
          {consentGiven && <Ionicons name="checkmark" size={18} color="#fff" />}
        </View>
        <Text style={styles.consentText}>
          I am {childName}'s parent/guardian and I consent to their use of Bible Buddy
        </Text>
      </TouchableOpacity>
    </Animated.View>
  );

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {/* Header */}
      <LinearGradient colors={['#667eea', '#764ba2']} style={styles.header}>
        <SafeAreaView edges={['top']} style={styles.headerContent}>
          <TouchableOpacity onPress={() => step > 1 ? setStep(step - 1) : router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <View style={styles.progressContainer}>
            {[1, 2, 3].map((s) => (
              <View key={s} style={[styles.progressDot, step >= s && styles.progressDotActive]} />
            ))}
          </View>
          <View style={{ width: 40 }} />
        </SafeAreaView>
      </LinearGradient>

      {/* Content */}
      <ScrollView style={styles.scrollContent} contentContainerStyle={styles.scrollContainer} showsVerticalScrollIndicator={false}>
        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}
      </ScrollView>

      {/* Footer */}
      <View style={styles.footer}>
        <TouchableOpacity style={styles.continueButton} onPress={handleContinue} disabled={isLoading} activeOpacity={0.9}>
          <LinearGradient
            colors={step === 3 ? ['#4ECDC4', '#44A08D'] : ['#FF6B6B', '#FF8E53']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.continueGradient}
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <>
                <Text style={styles.continueText}>
                  {step === 3 ? "🎉 Let's Start!" : 'Continue'}
                </Text>
                <Ionicons name="arrow-forward-circle" size={26} color="#fff" />
              </>
            )}
          </LinearGradient>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8F9FF' },
  header: { paddingBottom: 20 },
  headerContent: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingTop: 8 },
  backButton: { width: 40, height: 40, borderRadius: 20, backgroundColor: 'rgba(255,255,255,0.2)', alignItems: 'center', justifyContent: 'center' },
  progressContainer: { flexDirection: 'row', gap: 8 },
  progressDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: 'rgba(255,255,255,0.3)' },
  progressDotActive: { backgroundColor: '#fff', width: 28 },
  scrollContent: { flex: 1 },
  scrollContainer: { padding: 24 },
  stepContent: { flex: 1 },
  stepHeader: { alignItems: 'center', marginBottom: 32 },
  emojiCircle: { width: 100, height: 100, borderRadius: 50, backgroundColor: '#EDE9FE', alignItems: 'center', justifyContent: 'center', marginBottom: 16 },
  headerEmoji: { fontSize: 48 },
  stepTitle: { fontSize: 28, fontWeight: '800', color: '#2D3436', textAlign: 'center' },
  stepSubtitle: { fontSize: 16, color: '#636E72', marginTop: 8, textAlign: 'center' },
  inputSection: { marginTop: 20 },
  inputLabel: { fontSize: 16, fontWeight: '700', color: '#2D3436', marginBottom: 12 },
  inputContainer: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', borderRadius: 20, paddingHorizontal: 16, shadowColor: '#6C5CE7', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.15, shadowRadius: 12, elevation: 6 },
  inputIcon: { marginRight: 12 },
  textInput: { flex: 1, fontSize: 18, color: '#2D3436', paddingVertical: 18 },
  ageGrid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: 12 },
  ageCard: { width: (width - 60) / 2, padding: 20, borderRadius: 24, alignItems: 'center', borderWidth: 3, position: 'relative' },
  ageEmoji: { fontSize: 40, marginBottom: 8 },
  ageLabel: { fontSize: 16, fontWeight: '700' },
  ageDesc: { fontSize: 12, color: '#636E72', marginTop: 4 },
  checkBadge: { position: 'absolute', top: 12, right: 12, width: 26, height: 26, borderRadius: 13, alignItems: 'center', justifyContent: 'center' },
  safetyCard: { backgroundColor: '#fff', borderRadius: 24, padding: 20, shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.08, shadowRadius: 12, elevation: 4, marginBottom: 20 },
  safetyItem: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  safetyIconCircle: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center', marginRight: 14 },
  safetyText: { flex: 1, fontSize: 15, color: '#2D3436', fontWeight: '500' },
  consentBox: { flexDirection: 'row', alignItems: 'flex-start', backgroundColor: '#fff', padding: 18, borderRadius: 20, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 8, elevation: 3 },
  checkbox: { width: 28, height: 28, borderRadius: 8, borderWidth: 2, borderColor: '#6C5CE7', alignItems: 'center', justifyContent: 'center', marginRight: 14, marginTop: 2 },
  checkboxChecked: { backgroundColor: '#6C5CE7' },
  consentText: { flex: 1, fontSize: 15, color: '#2D3436', lineHeight: 22 },
  footer: { padding: 20, paddingBottom: 30 },
  continueButton: { borderRadius: 20, overflow: 'hidden', shadowColor: '#FF6B6B', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.35, shadowRadius: 16, elevation: 8 },
  continueGradient: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 18, gap: 10 },
  continueText: { color: '#fff', fontSize: 20, fontWeight: '700' },
});
