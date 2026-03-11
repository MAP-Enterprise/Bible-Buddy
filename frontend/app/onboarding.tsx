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
  StatusBar,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useAuthContext } from '../contexts/AuthContext';
import VoicePicker from '../components/VoicePicker';

const AGE_TIERS = [
  { value: '4-6', label: '4-6 years', emoji: '\ud83e\uddd2', desc: 'Preschool', color: '#FF6B6B', bg: '#FFE8E8' },
  { value: '7-9', label: '7-9 years', emoji: '\ud83d\udc67', desc: 'Early Elementary', color: '#4ECDC4', bg: '#E0F7F5' },
  { value: '10-12', label: '10-12 years', emoji: '\ud83e\uddd1', desc: 'Upper Elementary', color: '#FFD93D', bg: '#FFF8E0' },
  { value: '13-18', label: '13-18 years', emoji: '\ud83c\udf93', desc: 'Teen', color: '#6C5CE7', bg: '#EDE9FE' },
];

const TOTAL_STEPS = 4;

export default function OnboardingScreen() {
  const { isAuthenticated, addChild } = useAuthContext();
  const [step, setStep] = useState(1);
  const [childName, setChildName] = useState('');
  const [selectedAgeTier, setSelectedAgeTier] = useState('');
  const [consentGiven, setConsentGiven] = useState(false);
  const [consentNameInput, setConsentNameInput] = useState('');
  const [selectedVoice, setSelectedVoice] = useState('EXAVITQu4vr4xnSDxMaL');
  const [isLoading, setIsLoading] = useState(false);
  
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(30)).current;

  useEffect(() => {
    fadeAnim.setValue(0);
    slideAnim.setValue(30);
    Animated.parallel([
      Animated.timing(fadeAnim, { toValue: 1, duration: 500, useNativeDriver: true }),
      Animated.timing(slideAnim, { toValue: 0, duration: 500, useNativeDriver: true }),
    ]).start();
  }, [step]);

  const showAlert = (title: string, message: string) => {
    if (Platform.OS === 'web') {
      window.alert(`${title}: ${message}`);
    } else {
      Alert.alert(title, message);
    }
  };

  const handleContinue = async () => {
    if (step === 1) {
      if (!childName.trim()) {
        showAlert('Oops!', "Please enter your child's name");
        return;
      }
      setStep(2);
    } else if (step === 2) {
      if (!selectedAgeTier) {
        showAlert('One more thing!', 'Please select an age group');
        return;
      }
      setStep(3);
    } else if (step === 3) {
      // Voice selection — always has a default, so just continue
      setStep(4);
    } else if (step === 4) {
      if (!consentGiven) {
        showAlert('Consent Required', 'Please check the consent box to continue');
        return;
      }
      if (consentNameInput.trim().toLowerCase() !== childName.trim().toLowerCase()) {
        showAlert('Verification Failed', "Please type your child's name exactly to verify your consent");
        return;
      }
      await createChildProfile();
    }
  };

  const createChildProfile = async () => {
    setIsLoading(true);
    try {
      if (isAuthenticated) {
        const result = await addChild(childName.trim(), selectedAgeTier, selectedVoice);
        if (!result.success) {
          showAlert('Error', result.error || 'Failed to create profile');
          setIsLoading(false);
          return;
        }
      }
      router.replace('/');
    } catch {
      showAlert('Error', 'Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const renderStep1 = () => (
    <Animated.View style={[styles.stepContent, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}>
      <View style={styles.stepHeader}>
        <View style={styles.emojiCircle}>
          <Text style={styles.headerEmoji}>{'\ud83d\udc4b'}</Text>
        </View>
        <Text style={styles.stepTitle}>Add a Child Profile</Text>
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
            data-testid="child-name-input"
          />
        </View>
      </View>
    </Animated.View>
  );

  const renderStep2 = () => (
    <Animated.View style={[styles.stepContent, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}>
      <View style={styles.stepHeader}>
        <View style={[styles.emojiCircle, { backgroundColor: '#FFF8E0' }]}>
          <Text style={styles.headerEmoji}>{'\ud83c\udf82'}</Text>
        </View>
        <Text style={styles.stepTitle}>Hi, {childName}!</Text>
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
            data-testid={`age-card-${tier.value}`}
          >
            <Text style={{ fontSize: 40, textAlign: 'center' }}>{tier.emoji}</Text>
            <Text style={{ fontSize: 16, fontWeight: '700', color: '#2D3436', marginTop: 8, textAlign: 'center' }}>{tier.label}</Text>
            <Text style={{ fontSize: 12, color: '#636E72', marginTop: 4, textAlign: 'center' }}>{tier.desc}</Text>
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
        <View style={[styles.emojiCircle, { backgroundColor: '#F0ECFF' }]}>
          <Ionicons name="mic" size={42} color="#6C5CE7" />
        </View>
        <Text style={styles.stepTitle}>Choose a Voice</Text>
        <Text style={styles.stepSubtitle}>Pick who reads Bible answers to {childName}</Text>
      </View>

      <VoicePicker selectedVoiceId={selectedVoice} onSelect={setSelectedVoice} />
    </Animated.View>
  );

  const renderStep4 = () => (
    <Animated.View style={[styles.stepContent, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}>
      <View style={styles.stepHeader}>
        <View style={[styles.emojiCircle, { backgroundColor: '#E0F7F5' }]}>
          <Text style={styles.headerEmoji}>{'\ud83d\udee1\ufe0f'}</Text>
        </View>
        <Text style={styles.stepTitle}>Parental Consent</Text>
        <Text style={styles.stepSubtitle}>COPPA-compliant privacy protection</Text>
      </View>
      
      {/* Data Disclosure */}
      <View style={styles.safetyCard}>
        <Text style={{ fontSize: 15, fontWeight: '700', color: '#2D3436', marginBottom: 12 }}>What we collect:</Text>
        {[
          { icon: 'person', color: '#6C5CE7', text: "Child's first name and age group" },
          { icon: 'chatbubble', color: '#4ECDC4', text: 'Bible-related questions asked' },
          { icon: 'mic', color: '#FF6B6B', text: 'Voice input (processed in real-time, not stored)' },
        ].map((item, i) => (
          <View key={i} style={styles.safetyItem}>
            <View style={[styles.safetyIconCircle, { backgroundColor: `${item.color}20` }]}>
              <Ionicons name={item.icon as any} size={20} color={item.color} />
            </View>
            <Text style={styles.safetyText}>{item.text}</Text>
          </View>
        ))}
        
        <View style={{ marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: '#F0F0F0' }}>
          <Text style={{ fontSize: 15, fontWeight: '700', color: '#2D3436', marginBottom: 12 }}>We do NOT collect:</Text>
          {['Last name or full identity', 'Location, photos, or contact info', 'Any data from external sources'].map((text, i) => (
            <View key={i} style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8, gap: 8 }}>
              <Ionicons name="close-circle" size={18} color="#FF6B6B" />
              <Text style={{ fontSize: 14, color: '#636E72' }}>{text}</Text>
            </View>
          ))}
        </View>
        
        <View style={{ marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: '#F0F0F0' }}>
          <Text style={{ fontSize: 15, fontWeight: '700', color: '#2D3436', marginBottom: 8 }}>Your rights:</Text>
          {['View all conversations in Parent Dashboard', 'Delete child profile and data anytime', 'Revoke consent and deactivate access'].map((text, i) => (
            <View key={i} style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8, gap: 8 }}>
              <Ionicons name="checkmark-circle" size={18} color="#4ECDC4" />
              <Text style={{ fontSize: 14, color: '#636E72' }}>{text}</Text>
            </View>
          ))}
        </View>
      </View>
      
      {/* Consent Checkbox */}
      <TouchableOpacity style={styles.consentBox} onPress={() => setConsentGiven(!consentGiven)} activeOpacity={0.8} data-testid="consent-checkbox">
        <View style={[styles.checkbox, consentGiven && styles.checkboxChecked]}>
          {consentGiven && <Ionicons name="checkmark" size={18} color="#fff" />}
        </View>
        <Text style={styles.consentText}>
          I am {childName}'s parent/guardian and I consent to Bible Buddy collecting the data described above for the purpose of providing age-appropriate Bible education.
        </Text>
      </TouchableOpacity>

      {/* Name Verification */}
      {consentGiven && (
        <View style={{ marginTop: 16 }}>
          <Text style={{ fontSize: 14, fontWeight: '700', color: '#2D3436', marginBottom: 8 }}>
            To verify, please type your child's name:
          </Text>
          <View style={styles.inputContainer}>
            <Ionicons name="shield-checkmark" size={22} color="#4ECDC4" style={styles.inputIcon} />
            <TextInput
              style={styles.textInput}
              value={consentNameInput}
              onChangeText={setConsentNameInput}
              placeholder={`Type "${childName}" to confirm`}
              placeholderTextColor="#AAA"
              data-testid="consent-name-input"
            />
          </View>
        </View>
      )}
    </Animated.View>
  );

  const getButtonColors = (): [string, string] => {
    if (step === 4) return ['#4ECDC4', '#44A08D'];
    if (step === 3) return ['#6C5CE7', '#A29BFE'];
    return ['#FF6B6B', '#FF8E53'];
  };

  const getButtonText = () => {
    if (step === 4) return "Let's Start!";
    return 'Continue';
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      <LinearGradient colors={['#667eea', '#764ba2']} style={styles.header}>
        <SafeAreaView edges={['top']} style={styles.headerContent}>
          <TouchableOpacity onPress={() => step > 1 ? setStep(step - 1) : router.back()} style={styles.backButton} data-testid="onboarding-back-btn">
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <View style={styles.progressContainer}>
            {Array.from({ length: TOTAL_STEPS }, (_, i) => i + 1).map((s) => (
              <View key={s} style={[styles.progressDot, step >= s && styles.progressDotActive]} />
            ))}
          </View>
          <View style={{ width: 40 }} />
        </SafeAreaView>
      </LinearGradient>

      <ScrollView style={styles.scrollContent} contentContainerStyle={styles.scrollContainer} showsVerticalScrollIndicator={false}>
        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}
        {step === 4 && renderStep4()}
      </ScrollView>

      <View style={styles.footer}>
        <TouchableOpacity style={styles.continueButton} onPress={handleContinue} disabled={isLoading} activeOpacity={0.9} data-testid="onboarding-continue-btn">
          <LinearGradient
            colors={getButtonColors()}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.continueGradient}
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <>
                <Text style={styles.continueText}>{getButtonText()}</Text>
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
  scrollContainer: { padding: 24, paddingBottom: 40 },
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
  ageGrid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: 12 } as any,
  ageCard: { width: '47%' as any, padding: 20, borderRadius: 24, alignItems: 'center' as const, borderWidth: 3, position: 'relative' as const, minHeight: 140 },
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
