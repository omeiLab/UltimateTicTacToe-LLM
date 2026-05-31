import torch
import torch.nn as nn
import torch.nn.functional as F

class ResidualBlock(nn.Module):
    def __init__(self, channels):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)
        
    def forward(self, x):
        residual = x
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += residual
        return F.relu(out)

class UTTTNet(nn.Module):
    def __init__(self, num_res_blocks=3, num_channels=64):
        super(UTTTNet, self).__init__()

        self.conv_init = nn.Conv2d(
            5,
            num_channels,
            kernel_size=3,
            padding=1,
            bias=False
        )
        self.bn_init = nn.BatchNorm2d(num_channels)

        self.res_blocks = nn.ModuleList(
            [ResidualBlock(num_channels) for _ in range(num_res_blocks)]
        )

        self.policy_conv = nn.Conv2d(
            num_channels,
            1,
            kernel_size=1,
            bias=True
        )

        self.value_conv = nn.Conv2d(
            num_channels,
            1,
            kernel_size=1,
            bias=False
        )
        self.value_bn = nn.BatchNorm2d(1)

        self.value_fc1 = nn.Linear(1 * 9 * 9, 64)
        self.value_fc2 = nn.Linear(64, 1)

    def forward(self, x):
        x = F.relu(self.bn_init(self.conv_init(x)))

        for block in self.res_blocks:
            x = block(x)

        p = self.policy_conv(x)
        p = p.view(p.size(0), 9, 9)

        logits_list = []

        for m in range(9):
            macro_row, macro_col = m // 3, m % 3

            r_start = macro_row * 3
            r_end = r_start + 3
            c_start = macro_col * 3
            c_end = c_start + 3

            micro_board = p[
                :,
                r_start:r_end,
                c_start:c_end
            ].reshape(p.size(0), 9)

            logits_list.append(micro_board)

        policy_logits = torch.cat(logits_list, dim=1)

        v = F.relu(self.value_bn(self.value_conv(x)))
        v = v.view(v.size(0), -1)
        v = F.relu(self.value_fc1(v))
        value = torch.tanh(self.value_fc2(v))

        return policy_logits, value