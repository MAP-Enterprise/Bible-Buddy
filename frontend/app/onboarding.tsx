import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

const AGE_TIERS = [
  { value: '4-6', label: '4-6 years', emoji: '🧒', desc: 'Preschool' },
  { value: '7-9', label: '7-9 years', emoji: '👧', desc: 'Early Elementary' },
  { value: '10-12', label: '10-12 years', emoji: '🧑', desc: 'Upper Elementary' },
  { value: '13-18', label: '13-18 years', emoji: '👨‍🎓', desc: 'Teen' },
];

export default function OnboardingScreen() {
  const [step, setStep] = useState(1);
  const [childName, setChildName] = useState('');
  const [selectedAgeTier, setSelectedAgeTier] = useState('');
  const [consentGiven, setConsentGiven] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleContinue = async () => {
    if (step === 1) {
      if (!childName.trim()) {
        Alert.alert('Name Required', 'Please enter your child\'s name');
        return;
      }
      setStep(2);
    } else if (step === 2) {
      if (!selectedAgeTier) {
        Alert.alert('Age Required', 'Please select your child\'s age group');
        return;
      }
      setStep(3);
    } else if (step === 3) {
      if (!consentGiven) {
        Alert.alert('Consent Required', 'Please provide parental consent to continue');
        return;
      }
      await createChildProfile();
    }
  };

  const createChildProfile = async () => {
    setIsLoading(true);
    try {
      // Create a local child profile for guest mode
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
      
      // Navigate to chat
      router.replace('/chat');
    } catch (error) {
      console.error('Error creating profile:', error);
      Alert.alert('Error', 'Failed to create profile. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const renderStep1 = () => (
    <View style={styles.stepContainer}>
      <View style={styles.stepHeader}>
        <Text style={styles.emoji}>👋</Text>
        <Text style={styles.stepTitle}>Welcome to Bible Buddy!</Text>
        <Text style={styles.stepSubtitle}>Let's set up your child's profile</Text>
      </View>
      
      <View style={styles.inputContainer}>
        <Text style={styles.inputLabel}>What's your child's name?</Text>
        <TextInput
          style={styles.textInput}
          value={childName}
          onChangeText={setChildName}
          placeholder="Enter name"
          placeholderTextColor="#999"
          autoFocus
        />
      </View>
    </View>
  );

  const renderStep2 = () => (
    <View style={styles.stepContainer}>
      <View style={styles.stepHeader}>
        <Text style={styles.emoji}>🎂</Text>
        <Text style={styles.stepTitle}>Hi, {childName}!</Text>
        <Text style={styles.stepSubtitle}>What age group fits best?</Text>
      </View>
      
      <View style={styles.ageTierContainer}>
        {AGE_TIERS.map((tier) => (
          <TouchableOpacity
            key={tier.value}
            style={[
              styles.ageTierCard,
              selectedAgeTier === tier.value && styles.ageTierCardActive,
            ]}
            onPress={() => setSelectedAgeTier(tier.value)}
          >
            <Text style={styles.ageTierEmoji}>{tier.emoji}</Text>
            <View style={styles.ageTierInfo}>
              <Text style={[
                styles.ageTierLabel,
                selectedAgeTier === tier.value && styles.ageTierLabelActive,
              ]}>
                {tier.label}
              </Text>
              <Text style={styles.ageTierDesc}>{tier.desc}</Text>
            </View>
            {selectedAgeTier === tier.value && (
              <Ionicons name="checkmark-circle" size={24} color="#4A90D9" />
            )}
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );

  const renderStep3 = () => (
    <View style={styles.stepContainer}>
      <View style={styles.stepHeader}>
        <Text style={styles.emoji}>🛡️</Text>
        <Text style={styles.stepTitle}>Parental Consent</Text>
        <Text style={styles.stepSubtitle}>We keep your child safe</Text>
      </View>
      
      <View style={styles.consentContainer}>
        <View style={styles.consentInfo}>
          <View style={styles.consentItem}>
            <Ionicons name="shield-checkmark" size={24} color="#27AE60" />
            <Text style={styles.consentText}>All conversations are age-appropriate</Text>
          </View>
          <View style={styles.consentItem}>
            <Ionicons name="eye-off" size={24} color="#27AE60" />
            <Text style={styles.consentText}>No personal data collection</Text>
          </View>
          <View style={styles.consentItem}>
            <Ionicons name="lock-closed" size={24} color="#27AE60" />
            <Text style={styles.consentText}>Content filtering for safety</Text>
          </View>
          <View style={styles.consentItem}>
            <Ionicons name="people" size={24} color="#27AE60" />
            <Text style={styles.consentText}>Parent dashboard available</Text>
          </View>
        </View>
        
        <TouchableOpacity
          style={styles.consentCheckbox}
          onPress={() => setConsentGiven(!consentGiven)}
        >
          <View style={[styles.checkbox, consentGiven && styles.checkboxChecked]}>
            {consentGiven && <Ionicons name="checkmark" size={18} color="#fff" />}
          </View>
          <Text style={styles.consentCheckboxText}>
            I am {childName}'s parent/guardian and I consent to their use of Bible Buddy
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => step > 1 ? setStep(step - 1) : router.back()}>
          <Ionicons name="arrow-back" size={24} color="#4A90D9" />
        </TouchableOpacity>
        <View style={styles.stepIndicator}>
          {[1, 2, 3].map((s) => (
            <View key={s} style={[styles.stepDot, step >= s && styles.stepDotActive]} />
          ))}
        </View>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView style={styles.content} contentContainerStyle={styles.contentContainer}>
        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}
      </ScrollView>

      <View style={styles.footer}>
        <TouchableOpacity
          style={[styles.continueButton, isLoading && styles.buttonDisabled]}
          onPress={handleContinue}
          disabled={isLoading}
        >
          {isLoading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <Text style={styles.continueButtonText}>
                {step === 3 ? "Let's Start!" : 'Continue'}
              </Text>
              <Ionicons name="arrow-forward" size={20} color="#fff" />
            </>
          )}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F0F7FF' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 20, paddingVertical: 16 },
  stepIndicator: { flexDirection: 'row', gap: 8 },
  stepDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#D1E3F8' },
  stepDotActive: { backgroundColor: '#4A90D9', width: 24 },
  content: { flex: 1 },
  contentContainer: { paddingHorizontal: 24 },
  stepContainer: { flex: 1 },
  stepHeader: { alignItems: 'center', marginBottom: 32 },
  emoji: { fontSize: 64, marginBottom: 16 },
  stepTitle: { fontSize: 28, fontWeight: '700', color: '#2C3E50', textAlign: 'center' },
  stepSubtitle: { fontSize: 16, color: '#666', marginTop: 8, textAlign: 'center' },
  inputContainer: { marginTop: 24 },
  inputLabel: { fontSize: 16, fontWeight: '600', color: '#333', marginBottom: 12 },
  textInput: { backgroundColor: '#fff', borderRadius: 16, paddingHorizontal: 20, paddingVertical: 16, fontSize: 18, borderWidth: 2, borderColor: '#E8F0FE' },
  ageTierContainer: { gap: 12 },
  ageTierCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', padding: 16, borderRadius: 16, borderWidth: 2, borderColor: '#E8F0FE' },
  ageTierCardActive: { borderColor: '#4A90D9', backgroundColor: '#F0F7FF' },
  ageTierEmoji: { fontSize: 36, marginRight: 16 },
  ageTierInfo: { flex: 1 },
  ageTierLabel: { fontSize: 18, fontWeight: '600', color: '#333' },
  ageTierLabelActive: { color: '#4A90D9' },
  ageTierDesc: { fontSize: 14, color: '#888', marginTop: 2 },
  consentContainer: { marginTop: 16 },
  consentInfo: { backgroundColor: '#fff', borderRadius: 16, padding: 20, marginBottom: 20 },
  consentItem: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  consentText: { fontSize: 15, color: '#333', marginLeft: 12, flex: 1 },
  consentCheckbox: { flexDirection: 'row', alignItems: 'flex-start', backgroundColor: '#fff', padding: 16, borderRadius: 16 },
  checkbox: { width: 26, height: 26, borderRadius: 6, borderWidth: 2, borderColor: '#4A90D9', alignItems: 'center', justifyContent: 'center', marginRight: 12, marginTop: 2 },
  checkboxChecked: { backgroundColor: '#4A90D9' },
  consentCheckboxText: { flex: 1, fontSize: 15, color: '#333', lineHeight: 22 },
  footer: { paddingHorizontal: 24, paddingVertical: 20 },
  continueButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#4A90D9', paddingVertical: 18, borderRadius: 16 },
  buttonDisabled: { backgroundColor: '#B8D4F0' },
  continueButtonText: { color: '#fff', fontSize: 18, fontWeight: '600', marginRight: 8 },
});
