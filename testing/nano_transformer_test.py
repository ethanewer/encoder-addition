import sys

sys.path.append("..")

import torch
import torch.nn.functional as F
from torch import Tensor
from transformers import GPT2Config, GPT2LMHeadModel, GPT2Model  # type: ignore

from nano_transformer import (
    Transformer,
    TransformerConfig,
    TransformerLMHead,
    flat_cross_entropy,
)


def build_identical_models(
    lm: bool,
    n_positions=80,
    n_embd=256,
    n_layer=12,
    n_head=8,
) -> tuple[GPT2Model | GPT2LMHeadModel, Transformer | TransformerLMHead]:
    cfg1 = GPT2Config(
        n_positions=2 * n_positions,
        n_embd=n_embd,
        n_layer=n_layer,
        n_head=n_head,
        vocab_size=50257,
        resid_pdrop=0.0,
        embd_pdrop=0.0,
        attn_pdrop=0.0,
        use_cache=False,
    )

    cfg2 = TransformerConfig(
        n_positions=2 * n_positions,
        vocab_size=50257,
        n_embd=n_embd,
        n_layer=n_layer,
        n_head=n_head,
        dropout=0,
    )

    if lm:
        model1: GPT2Model | GPT2LMHeadModel = GPT2LMHeadModel(cfg1)
        model2: Transformer | TransformerLMHead = TransformerLMHead(cfg2)
    else:
        model1 = GPT2Model(cfg1)
        model2 = Transformer(cfg2)

    with torch.no_grad():
        for (n1, p1), (n2, p2) in zip(
            model1.named_parameters(), model2.named_parameters()
        ):
            assert n1 == n2
            if p1.shape != p2.shape:
                assert p1.shape[::-1] == p2.shape
                p1.copy_(p2.T)
            else:
                p1.copy_(p2)

    for (n1, p1), (n2, p2) in zip(model1.named_parameters(), model2.named_parameters()):
        assert n1 == n2
        if p1.shape != p2.shape:
            assert p1.shape[::-1] == p2.shape
            assert torch.all(p1 == p2.T)
        else:
            assert torch.all(p1 == p2)

    return model1, model2


def test_causal_outputs(
    forward_idxs: Tensor,
    n_positions=80,
    n_embd=256,
    n_layer=12,
    n_head=8,
) -> None:
    model = Transformer(
        TransformerConfig(
            n_positions=2 * n_positions,
            n_embd=n_embd,
            n_layer=n_layer,
            n_head=n_head,
            dropout=0,
        )
    )

    x = torch.randn(2, n_positions, n_embd)

    y1 = model._Transformer__decoder_forward(x, is_causal=True)
    y2 = model._Transformer__encoder_forward(
        x, is_causal=True, forward_idxs=forward_idxs
    )

    assert torch.allclose(
        y1[:, forward_idxs],
        y2[:, forward_idxs],
        rtol=1e-6,
        atol=1e-6,
    )


def test_causal_gradients(
    forward_idxs: Tensor,
    n_positions=80,
    n_embd=256,
    n_layer=12,
    n_head=8,
) -> None:
    model = Transformer(
        TransformerConfig(
            n_positions=2 * n_positions,
            n_embd=n_embd,
            n_layer=n_layer,
            n_head=n_head,
            dropout=0,
        )
    )

    x = torch.randn(2, n_positions, n_embd)
    y_true = torch.randn(2, n_positions, n_embd)

    y1 = model._Transformer__decoder_forward(x, is_causal=True)
    loss1 = F.mse_loss(y1[:, forward_idxs], y_true[:, forward_idxs])
    loss1.backward()
    grads1 = {}
    for p_name, p in model.named_parameters():
        if p.grad is not None:
            grads1[p_name] = p.grad.clone()
            p.grad.zero_()

    y2 = model._Transformer__encoder_forward(
        x, is_causal=True, forward_idxs=forward_idxs
    )
    loss2 = F.mse_loss(y2[:, forward_idxs], y_true[:, forward_idxs])
    loss2.backward()
    grads2 = {}
    for p_name, p in model.named_parameters():
        if p.grad is not None:
            grads2[p_name] = p.grad.clone()
            p.grad.zero_()

    assert torch.allclose(loss1, loss2, rtol=1e-6, atol=1e-6)

    for p_name, p in model.named_parameters():
        if p.grad is not None:
            assert torch.allclose(
                grads1[p_name],
                grads2[p_name],
                rtol=1e-6,
                atol=1e-6,
            )


def test_outputs_huggingface(
    n_positions=80,
    n_embd=256,
    n_layer=12,
    n_head=8,
) -> None:
    model1, model2 = build_identical_models(False, n_positions, n_embd, n_layer, n_head)

    x = torch.randint(50256, (2, n_positions))

    y1 = model1(x).last_hidden_state
    y2 = model2(x)

    assert y1.shape == y2.shape
    assert torch.allclose(y1, y2)


def test_lm_outputs_huggingface(
    n_positions=80,
    n_embd=256,
    n_layer=12,
    n_head=8,
) -> None:
    model1, model2 = build_identical_models(True, n_positions, n_embd, n_layer, n_head)

    x = torch.randint(50256, (2, n_positions))

    y1 = model1(x).logits
    y2 = model2(x)

    assert y1.shape == y2.shape
    assert torch.allclose(y1, y2)


def test_lm_gradients_huggingface(
    n_positions=80,
    n_embd=256,
    n_layer=12,
    n_head=8,
) -> None:
    model1, model2 = build_identical_models(True, n_positions, n_embd, n_layer, n_head)

    x = torch.randint(50256, (2, n_positions))
    y_true = torch.randint(50256, (2, n_positions))

    y1 = model1(x).logits
    y2 = model2(x)

    loss1 = flat_cross_entropy(y1, y_true)
    loss2 = flat_cross_entropy(y2, y_true)

    assert torch.allclose(loss1, loss2)

    loss1.backward()
    loss2.backward()

    grads1 = {}
    for p_name, p in model1.named_parameters():
        if p.grad is not None:
            grads1[p_name] = p.grad

    grads2 = {}
    for p_name, p in model2.named_parameters():
        if p.grad is not None:
            grads2[p_name] = p.grad

    for p_name, p in model1.named_parameters():
        if p.grad is not None:
            assert torch.allclose(grads1[p_name], grads2[p_name])


if __name__ == "__main__":
    test_outputs_huggingface()
    test_lm_outputs_huggingface()
    test_lm_gradients_huggingface()

    for forward_idxs in [torch.arange(0, 80, 1), torch.arange(0, 80, 2)]:
        test_causal_outputs(forward_idxs, n_positions=80)
        test_causal_gradients(forward_idxs, n_positions=80)

    print("all tests passed :D")