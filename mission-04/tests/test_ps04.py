"""
Squadron Winograd Unit Tests for Mission 04:
  - DPO Loss Core & Vectorized Logps
  - Implicit Reward Extraction & Bradley-Terry Calibration
  - Length Bias Diagnostics & SimPO Objective
  - Activation Steering Vectors & Alignment Tax Audit

Station Officer: Muhammad Qasim Siddiqui (Security & Ethics Sentinel / Systems Architect)
"""

import pytest
import math
import torch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from importlib import import_module
dpo_mod = import_module("01_DPO_Loss_Core")
reward_mod = import_module("02_Implicit_Reward_Evaluator")
simpo_mod = import_module("03_Length_Bias_and_SimPO")
steering_mod = import_module("04_Activation_Steering_and_Audit")

get_batch_logps = dpo_mod.get_batch_logps
DPOLoss = dpo_mod.DPOLoss

compute_implicit_rewards = reward_mod.compute_implicit_rewards
evaluate_preference_accuracy = reward_mod.evaluate_preference_accuracy
compute_bradley_terry_calibration = reward_mod.compute_bradley_terry_calibration

compute_length_correlation = simpo_mod.compute_length_correlation
SimPOLoss = simpo_mod.SimPOLoss

extract_steering_vector = steering_mod.extract_steering_vector
ActivationSteeringHook = steering_mod.ActivationSteeringHook
MiniDecoderModel = steering_mod.MiniDecoderModel


def test_get_batch_logps_masking():
    """Verify logps gather correctly masks padding tokens."""
    batch_size = 2
    seq_len = 5
    vocab_size = 10

    logits = torch.randn(batch_size, seq_len, vocab_size)
    labels = torch.randint(0, vocab_size, (batch_size, seq_len))

    # Mask last 2 tokens
    labels[:, 3:] = -100

    logps_unnorm = get_batch_logps(logits, labels, average_log_prob=False)
    logps_norm = get_batch_logps(logits, labels, average_log_prob=True)

    assert logps_unnorm.shape == (batch_size,)
    assert logps_norm.shape == (batch_size,)
    # Normalized should equal unnorm divided by 3 (the 3 unpadded tokens)
    assert torch.allclose(logps_norm, logps_unnorm / 3.0, atol=1e-5)


def test_dpo_loss_gradient_isolation():
    """Verify DPOLoss updates policy parameters while leaving reference frozen."""
    dpo = DPOLoss(beta=0.1)

    p_w = torch.tensor([-1.5, -2.0], requires_grad=True)
    p_l = torch.tensor([-3.5, -4.0], requires_grad=True)
    ref_w = torch.tensor([-1.5, -2.0], requires_grad=False)
    ref_l = torch.tensor([-3.5, -4.0], requires_grad=False)

    loss, r_w, r_l = dpo(p_w, p_l, ref_w, ref_l)
    assert loss.item() > 0.0

    loss.backward()
    assert p_w.grad is not None
    assert p_l.grad is not None
    assert ref_w.grad is None
    assert ref_l.grad is None


def test_implicit_reward_margins():
    """Verify analytical implicit reward extraction and pairwise accuracy."""
    pi_w = torch.tensor([-10.0, -12.0])
    pi_l = torch.tensor([-15.0, -20.0])
    ref_w = torch.tensor([-12.0, -14.0])
    ref_l = torch.tensor([-13.0, -16.0])

    r_w, r_l, delta_r = compute_implicit_rewards(pi_w, pi_l, ref_w, ref_l, beta=0.1)
    # delta_w = [-10 - (-12), -12 - (-14)] = [2.0, 2.0] -> r_w = [0.2, 0.2]
    # delta_l = [-15 - (-13), -20 - (-16)] = [-2.0, -4.0] -> r_l = [-0.2, -0.4]
    assert torch.allclose(r_w, torch.tensor([0.2, 0.2]), atol=1e-4)
    assert torch.allclose(r_l, torch.tensor([-0.2, -0.4]), atol=1e-4)

    acc = evaluate_preference_accuracy(r_w, r_l)
    assert acc == 1.0


def test_bradley_terry_calibration():
    """Verify Bradley-Terry probability calibration calculation."""
    margins = torch.tensor([0.5, 1.2, -0.3, 2.5, 0.0])
    calib = compute_bradley_terry_calibration(margins, num_bins=4)

    assert "ece" in calib
    assert 0.0 <= calib["ece"] <= 1.0
    assert 0.0 <= calib["mean_predicted_prob"] <= 1.0


def test_simpo_loss_length_normalization():
    """Verify SimPO reference-free loss with target margin gamma."""
    simpo = SimPOLoss(beta=2.0, gamma=0.5)

    pi_w = torch.tensor([-20.0, -40.0])
    pi_l = torch.tensor([-30.0, -50.0])
    len_w = torch.tensor([10.0, 20.0]) # avg logp = -2.0
    len_l = torch.tensor([10.0, 25.0]) # avg logp = -3.0, -2.0

    loss, r_w, r_l = simpo(pi_w, pi_l, len_w, len_l)
    assert loss.item() > 0.0
    assert r_w.shape == pi_w.shape
    assert r_l.shape == pi_l.shape


def test_activation_steering_hook():
    """Verify ActivationSteeringHook alters target layer output when active."""
    d_model = 32
    model = MiniDecoderModel(num_layers=2, d_model=d_model)

    contrast_pairs = [
        (torch.randn(1, 4, d_model) + 0.5, torch.randn(1, 4, d_model) - 0.5)
        for _ in range(5)
    ]
    v_steer = extract_steering_vector(model, contrast_pairs, target_layer_idx=1)
    assert torch.allclose(torch.norm(v_steer), torch.tensor(1.0), atol=1e-4)

    hook = ActivationSteeringHook(model.layers[1], v_steer, alpha=1.5)
    test_x = torch.randn(1, 4, d_model)

    # 1. Output without hook
    logits_unsteered, _ = model(test_x)

    # 2. Output with hook
    hook.register()
    logits_steered, _ = model(test_x)
    assert not torch.allclose(logits_unsteered, logits_steered, atol=1e-4)

    # 3. Output after removing hook
    hook.remove()
    logits_restored, _ = model(test_x)
    assert torch.allclose(logits_unsteered, logits_restored, atol=1e-5)
